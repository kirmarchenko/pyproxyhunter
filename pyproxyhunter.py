# -*- coding: utf-8 -*-
import re
from collections import namedtuple
from datetime import datetime
from threading import activeCount, Thread

import requests
import socket
from lxml import html
from time import sleep
from urlparse import urlparse


class ProxyHunter(object):
    """
    This class search proxy files in google and then check every proxy if it's alive.
    After that, all fresh proxy with country names will be returned and can be stored to file.
    """
    def __init__(self, verbose=False, store=False, timeout=2, threads=200, pages=1, output_file=None):
        """
        :param verbose: bool, print various information about hunting process
        :param store: bool, save founded good proxies to file
        :param timeout: int, connection timeout via proxy
        :param threads: int, threads to check proxies
        :param pages: int, google pages to search *.txt files with proxy servers
        :param output_file: string, filename to save proxies
        """
        self.verbose = verbose
        self.store = store
        self.timeout = timeout
        self.threads = threads
        self.max_pages_to_search = pages
        if self.store:
            self.output_file = output_file or 'output.txt'

        self.Proxy = namedtuple('Proxy', ['server', 'country'])

    def print_if_verbose(self, message):
        """
        Would print a message if self.verbose is True
        :param message: string, message to print
        """
        if self.verbose:
            print message

    def collect_proxies(self):
        """
        Method to search in google for *.txt files with proxy servers
        :return: list of file urls
        """
        proxies = []
        for page in xrange(self.max_pages_to_search):
            response = requests.get(
                    'https://www.google.com/search?q=+":8080" +":3128" +":80" filetype:txt&start={}0'.format(page)
            )
            urls = html.fromstring(response.text).xpath('.//*[@id="ires"]//a/@href')
            for url in urls:
                # This monster regexp extracts link to *.txt file with proxy servers
                proxy_file = re.findall("/url\?q=((?!.*webcache)(?:(?:https?|ftp)://|www\.|ftp\.)[^'\r\n]+\.txt)", url)
                proxies += self.get_proxies(proxy_file)
        return proxies

    def get_proxies(self, urls):
        """
        Requests file, extracts proxy servers from it.
        :param urls: list with file urls
        :return: list with collected proxy servers
        """
        proxies = []
        for url in urls:
            result = urlparse(url)
            if not result.scheme:
                url = 'http://%s' % url
            if result.scheme == 'ftp':
                # We don't work with FTP
                return []
            self.print_if_verbose("Parsing %s" % url)

            try:
                response = requests.get(url, timeout=self.timeout)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, socket.timeout):
                self.print_if_verbose("Can't connect to %s" % url)
                return []
            if not response.ok:
                self.print_if_verbose("Can't connect to %s, status code: %d" % (url, response.status_code))
                return []
            proxies += re.findall('\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}\s*?[:]\s*?\d{1,5}', response.text)
            self.print_if_verbose("%d proxies received from %s \n" % (len(proxies), url))
        return proxies

    def proxy_is_alive(self, server):
        """
        Test the ability to connect to website via proxy server
        :param server: proxy server to check
        :return: False in case of any troubles, self.Proxy object if proxy server is good
        """
        proxies = {
            "http": 'http://%s/' % server.replace(' ', '')
        }

        try:
            response = requests.get('http://ip-api.com/json/?fields=country,status',
                                    proxies=proxies, timeout=self.timeout)
        except Exception as e:
            self.print_if_verbose(e.message)
            # Seems like something went wrong with connection.
            # Probably just dead or slow proxy, so
            return False

        try:
            info = response.json()
        except ValueError:
            return False

        if not info['status'] == 'fail':
            country = info['country']
            return self.Proxy(server, country)
        else:
            return False

    def check_proxy(self, proxy_to_check, proxy_list):
        """
        Check if proxy is good, if so - save it to list for good proxies
        :param proxy_to_check: proxy server to check
        :param proxy_list: list for good proxies
        """
        result = self.proxy_is_alive(proxy_to_check)

        if result:
            self.print_if_verbose("%s is alive" % proxy_to_check)
            proxy_list.append(result)
        else:
            self.print_if_verbose("%s is dead" % proxy_to_check)

    def check_proxies_multi_thread(self, proxies_to_check):
        """
        Get a list of proxies and test it with a number of threads.
        :param proxies_to_check: list with collected proxy servers
        :return: list of live and fast proxies
        """
        proxies = []
        print '%d proxy to check with %d threads. Please wait.' % (len(proxies_to_check),
                                                                   self.threads)
        start_time = datetime.now()

        for proxy in proxies_to_check:
            while activeCount() == self.threads:
                sleep(1)
            try:
                thread = Thread(target=self.check_proxy, args=(proxy, proxies))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print 'Exception: %s \nActive threads: %d' % (e, activeCount())

        while activeCount() > 1:
            sleep(1)
        finish_time = datetime.now()
        delta = (finish_time - start_time).seconds
        print 'Checked for {} seconds (about {} minutes). {} proxies are good.'.format(delta,
                                                                                       round(delta / 60., 1),
                                                                                       len(proxies))
        return proxies

    def save_results(self, proxy_list_to_store):
        """
        Saves good proxies to file, ordered by country name
        :param proxy_list_to_store: list with self.Proxy objects
        """
        proxy_list_to_store.sort(key=lambda data: data.country)

        with open(self.output_file, 'w') as good_proxy:
            for proxy in proxy_list_to_store:
                good_proxy.write('%s\t%s\n' % (proxy.server, proxy.country))
            print "%d fresh proxies saved to %s" % (len(proxy_list_to_store), self.output_file)

    def hunt(self):
        """
        Global method to collect, test, optionally save and return good proxies
        :return: list of self.Proxy objects
        """
        proxies = self.collect_proxies()
        live_proxies = self.check_proxies_multi_thread(proxies)

        if not live_proxies:
            print "It's weird, but no live proxy was found. " \
                  "Please, check if http://ip-api.com/ live now, and contact the developer."
            exit(1)

        if self.store:
            self.save_results(live_proxies)

        return live_proxies


if __name__ == '__main__':
    hunter = ProxyHunter(store=True)
    hunter.hunt()
