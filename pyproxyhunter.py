# -*- coding: utf-8 -*-
"""Python proxy hunter is a tool that will help you to get quickly a number
of free and fast proxy servers.
"""
import json
import os
import re
import socket

import requests

from collections import namedtuple
from threading import activeCount, Thread
from time import sleep
from urlparse import urlparse

from lxml import html

from requests.exceptions import ConnectionError, Timeout

from tqdm_progressbar import ModifiedTqdmProgressbar


def get_proxy_object():
    """Get a Proxy object to store server address and server country"""
    return namedtuple("Proxy", ["server", "country"])


class ProxyHunter(object):
    """This class search proxy files in google and check every proxy
    if it's alive. After that, all fresh proxy with country names will be
    returned and can be stored to file.
    """

    def __init__(self, verbose=False, store=False, timeout=2, threads=500,
                 pages=1, output_file=None):
        """:param verbose: bool, print various information about hunting process
        :param store: bool, save founded good proxies to file
        :param timeout: int, connection timeout via proxy in seconds
        :param threads: int, threads to check proxies
        :param pages: int, number of google pages to search for files with proxy servers
        :param output_file: string, filename to save proxies
        """
        self.verbose = verbose
        self.store = store
        self.timeout = timeout
        self.threads = threads
        self.max_pages_to_search = pages
        if self.store:
            self.output_file = os.path.abspath(output_file or "output.txt")
            store_dir = os.path.dirname(self.output_file)
            if not os.access(store_dir, os.W_OK):
                print "Can't save proxy servers to {} - not enough permissions.".format(self.output_file)
                exit(1)
            else:
                print "Proxy servers would be saved to {}.".format(self.output_file)

        self.proxy = get_proxy_object()

    def print_if_verbose(self, message):
        """Would print a message if self.verbose is True
        :param message: string, message to print
        """
        if self.verbose:
            print message

    def collect_proxies(self):
        """Method to search in google for *.txt files with proxy servers
        :return: list of file urls
        """
        proxies = []
        for page in xrange(self.max_pages_to_search):
            response = requests.get(
                    "https://www.google.com/search?q=+\":8080\" +\":3128\" +\":80\" filetype:txt&start={}0".format(page)
            )
            urls = html.fromstring(response.text).xpath(".//*[@id=\"ires\"]//a/@href")
            for url in urls:
                # This monster regexp extracts link to *.txt file with proxy servers
                proxy_file = re.findall("/url\?q=((?!.*webcache)(?:(?:https?|ftp)://|www\.|ftp\.)[^'\r\n]+\.txt)", url)
                proxies += self.get_proxies(proxy_file)
        return proxies

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
            if result.scheme == 'ftp':
                # We don't work with FTP
                return []
            self.print_if_verbose("Parsing {}".format(url))

            try:
                response = requests.get(url, timeout=self.timeout)
            except (ConnectionError, Timeout, socket.timeout):
                self.print_if_verbose("Can't connect to {}".format(url))
                return []
            if not response.ok:
                self.print_if_verbose("Can't connect to {}, status code: {}".format(url, response.status_code))
                return []
            proxies += re.findall('\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}\s*?[:]\s*?\d{1,5}', response.text)
            self.print_if_verbose("{} proxies received from {} \n".format(len(proxies), url))
        return proxies

    def get_proxy_info(self, server):
        """Test the ability to connect to website via proxy server
        :param server: proxy server to check
        :return: None in case of any troubles, self.proxy object if proxy server is good
        """
        proxies = {
            "http": "http://{}/".format(server.replace(' ', ''))
        }

        try:
            response = requests.get("http://ip-api.com/json/?fields=country,status",
                                    proxies=proxies, timeout=self.timeout)
            info = json.loads(response.text)
        except Exception as exception:
            self.print_if_verbose(exception.message)
            # Seems like something went wrong with connection.
            # Probably just dead or slow proxy, so
            return None

        try:
            if "status" not in info:
                return None
        except TypeError:  # Empty response
            return None
        if not info["status"] == "fail":
            country = info["country"]
            return self.proxy(server, country)
        else:
            return None

    def check_proxy(self, proxy_to_check, proxy_list, progress_bar):
        """Check if proxy is good, if so - save it to list for good proxies
        :param proxy_to_check: proxy server to check
        :param proxy_list: list for good proxies
        :param progress_bar: progress visualizer
        """
        result = self.get_proxy_info(proxy_to_check)

        progress_bar.update()

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
        print "\n{} proxy to check with {} threads. Please wait.\n".format(total_collected, self.threads)
        threads = []
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} ETA:{remaining}"
        check_bar = ModifiedTqdmProgressbar(total=total_collected, desc="Check progress", bar_format=bar_format,
                                            proxy_list=proxies, ncols=80)
        check_bar.clear()

        for proxy in proxies_to_check:
            while activeCount() == self.threads:
                sleep(1)
            try:
                thread = Thread(target=self.check_proxy, args=(proxy, proxies, check_bar))
                thread.daemon = True
                thread.start()
                threads.append(thread)
            except KeyboardInterrupt:
                print "\nOh, you want to break checking? " \
                      "Let me stop running threads and give you everything I've found."
                break
            except Exception as exception:
                print "Exception: {} \nActive threads: {}".format(exception, activeCount())

        for thread in threads:
            thread.join()

        check_bar.close()

        # print "{} proxies are good.".format(len(proxies))
        return proxies

    def save_results(self, proxy_list_to_store):
        """Saves good proxies to file, ordered by country name
        :param proxy_list_to_store: list with self.proxy objects
        """
        proxy_list_to_store.sort(key=lambda data: data.country)

        with open(self.output_file, "w") as good_proxy:
            for proxy in proxy_list_to_store:
                good_proxy.write("{}\t{}\n".format(proxy.server, proxy.country))
            print "{} fresh proxies saved to {}".format(len(proxy_list_to_store), self.output_file)

    def hunt(self):
        """Global method to collect, test, optionally save and return good proxies
        :return: list of self.proxy objects
        """
        proxies = self.collect_proxies()
        live_proxies = self.check_proxies_multi_thread(proxies)

        if not live_proxies:
            print "It's weird, but no live proxy was found. " \
                  "If you didn't press Ctrl+C, then, please, check if http://ip-api.com/ live now, " \
                  "and contact the developer."
            exit(1)

        if self.store:
            self.save_results(live_proxies)

        return live_proxies


if __name__ == "__main__":
    hunter = ProxyHunter(store=True)
    hunter.hunt()
