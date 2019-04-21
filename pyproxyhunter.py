# -*- coding: utf-8 -*-
"""Python proxy hunter is a tool that will help you to get quickly a number
of free and fast proxy servers.
"""
import json
import os
import re
import socket

from collections import namedtuple
from threading import Thread
from time import sleep

try:
    from Queue import Queue
except ImportError:
    from queue import Queue
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
import progressbar
import requests
from requests.exceptions import ConnectionError, Timeout

from lxml import html


def get_proxy_object():
    """Get a Proxy object to store server address and server country"""
    return namedtuple("Proxy", ["server", "country"])


class NoProxiesFoundError(Exception):
    pass


class ProxyHunter(object):
    """This class search proxy files in google and check every proxy
    if it's alive. After that, all fresh proxy with country names (optionally)
     will be returned and can be stored to file.
    """

    def __init__(self, verbose=False, store=False, timeout=2, threads=500,
                 pages=1, input_files=None, output_file=None, get_country_info=False):
        """:param verbose: bool, print various information about hunting process
        :param store: bool, save founded good proxies to file
        :param timeout: int, connection timeout via proxy in seconds
        :param threads: int, threads to check proxies
        :param pages: int, number of google pages to search for files with proxy servers
        :param input_files: string or list, filename(s) with proxy servers to check
        :param output_file: string, filename to save proxies
        :param get_country_info: bool, check country of origin, or just check if proxy is live
        """
        self.verbose = verbose
        self.store = store
        self.timeout = timeout
        self.threads = threads
        self.max_pages_to_search = pages
        self.get_country = get_country_info
        self.input_files = input_files
        if self.store:
            self.output_file = os.path.abspath(output_file or "output.txt")
            store_dir = os.path.dirname(self.output_file)
            if not os.access(store_dir, os.W_OK):
                print("Can't save proxy servers to {} - not enough permissions.".format(self.output_file))
                exit(1)
            else:
                print("Proxy servers would be saved to {}.".format(self.output_file))

        self.proxy = get_proxy_object()

    def print_if_verbose(self, message):
        """Would print a message if self.verbose is True
        :param message: string, message to print
        """
        if self.verbose:
            print(message)

    def collect_proxies(self):
        """Method to search in google for *.txt files with proxy servers,
        or load it from input file.
        :return: list of file urls
        """
        proxies = []
        if not self.input_files:
            for page in range(self.max_pages_to_search):
                response = requests.get(
                    "https://www.google.com/search?q=+\":8080\" +\":3128\" +\":80\" filetype:txt&start={}0".format(page)
                )
                urls = html.fromstring(response.text).xpath(".//*[@id=\"ires\"]//a/@href")
                for url in urls:
                    # This monster regexp extracts link to *.txt file with proxy servers
                    proxy_file = re.findall(
                        r"/url\?q=((?!.*webcache)(?:(?:https?|ftp)://|www\.|ftp\.)[^'\r\n]+\.txt)", url
                    )
                    proxies += self.get_proxies(proxy_file)
        else:
            if isinstance(self.input_files, str):
                self.input_files = [self.input_files]
            for input_file in self.input_files:
                try:
                    with open(input_file) as i_file:
                        proxies += self.extract_proxies_from_file(i_file.read())
                except IOError:
                    print('Couldn\'t read from "{}"'.format(input_file))
        if not proxies:
            raise NoProxiesFoundError('No proxies found!')
        return set(proxies)

    def get_proxies(self, urls):
        """Requests file, extracts proxy servers from it.
        :param urls: list with file urls
        :return: list with collected proxy servers
        """
        proxies = []
        for url in urls:
            result = urlparse(url)
            if not result.scheme:
                url = "http://{}".format(url)
            if result.scheme == "ftp":
                # We don't work with FTP
                continue
            self.print_if_verbose("Parsing {}".format(url))

            try:
                response = requests.get(url, timeout=self.timeout)
            except (ConnectionError, Timeout, socket.timeout):
                self.print_if_verbose("Can't connect to {}".format(url))
                continue
            if not response.ok:
                self.print_if_verbose(
                    "Can't connect to {}, status code: {}".format(url, response.status_code)
                )
                continue
            proxies += self.extract_proxies_from_file(response.text)
            self.print_if_verbose("{} proxies received from {} \n".format(len(proxies), url))
        return proxies

    @staticmethod
    def extract_proxies_from_file(file_content):
        return re.findall(
                r"\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}\s*?[:]\s*?\d{1,5}", file_content
            )

    def get_proxy_info(self, server):
        """Test the ability to connect to website via proxy server
        :param server: proxy server to check
        :return: None in case of any troubles, self.proxy object if proxy server is good
        """
        proxies = {
            "http": "http://{}/".format(server.replace(' ', ''))
        }

        try:
            response = requests.get(
                "http://ip-api.com/json/?fields=country,status" if self.get_country else "http://ip.jsontest.com/",
                proxies=proxies, timeout=self.timeout
            )
            info = json.loads(response.text)
        except Exception as exception:
            self.print_if_verbose(exception.args)
            # Seems like something went wrong with connection.
            # Probably just dead or slow proxy, so
            return None

        try:
            if "status" not in info:
                if self.get_country:
                    return None
                else:
                    return None if "ip" not in info else self.proxy(server, "")
        except TypeError:  # Empty response
            return None
        if not info["status"] == "fail":
            country = info.get("country", "Unknown")
            return self.proxy(server, country)
        else:
            return None

    def check_proxy(self, queue, proxy_list, progress_bar, total):
        """Check if proxy is good, if so - save it to list for good proxies
        :param queue: queue with proxy servers to check
        :param proxy_list: list for good proxies
        :param progress_bar: progress visualizer
        """
        while not queue.empty():
            proxy_to_check = queue.get()
            result = self.get_proxy_info(proxy_to_check)

            progress_bar.update(total - queue.qsize())

            if result is not None:
                self.print_if_verbose("{} is alive".format(proxy_to_check))
                proxy_list.append(result)
            else:
                self.print_if_verbose("{} is dead".format(proxy_to_check))

    def check_proxies_multi_thread(self, proxies_to_check):
        """Get a list of proxies and test it with a number of threads.
        :param proxies_to_check: list with collected proxy servers
        :return: list of live and fast proxies
        """
        proxies = []
        total_collected = len(proxies_to_check)
        start_msg = "\n{} proxy to check with {} threads. Please wait.\n"
        print(start_msg.format(total_collected, self.threads))
        threads = []
        progress_bar = progressbar.ProgressBar(max_value=total_collected)

        queue = Queue()

        for proxy in proxies_to_check:
            queue.put(proxy)

        for _ in range(self.threads):
            thread = Thread(target=self.check_proxy, args=(queue, proxies, progress_bar, total_collected))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        try:
            while not queue.empty():
                for thread in threads:
                    thread.join(1)
        except KeyboardInterrupt:
            print("\nOh, you want to break checking? "
                  "Let me stop running threads and give you everything I've found.")

        progress_bar.finish()
        return proxies

    def save_results(self, proxy_list_to_store):
        """Saves good proxies to file, ordered by country name
        :param proxy_list_to_store: list with self.proxy objects
        """
        proxy_list_to_store.sort(key=lambda data: data.country)

        with open(self.output_file, "w") as good_proxy:
            for proxy in proxy_list_to_store:
                good_proxy.write("{}\t{}\n".format(proxy.server, proxy.country))
            print("{} fresh proxies saved to {}".format(len(proxy_list_to_store), self.output_file))

    def hunt(self):
        """Global method to collect, test, optionally save and return good proxies
        :return: list of self.proxy objects
        """
        proxies = self.collect_proxies()
        live_proxies = self.check_proxies_multi_thread(proxies)

        sleep(0.02)
        if not live_proxies:
            print("It's weird, but no live proxy was found. "
                  "If you think it's a mistake - please, contact the developer.")
            exit(1)

        if self.store:
            self.save_results(live_proxies)

        return live_proxies


if __name__ == "__main__":
    HUNTER = ProxyHunter(store=True)
    HUNTER.hunt()
