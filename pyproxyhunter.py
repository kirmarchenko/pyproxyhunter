# -*- coding: utf-8 -*-
import socket
import re
import requests
from time import sleep
from urlparse import urlparse
from lxml import html
from threading import activeCount, Thread
from datetime import datetime

__author__ = 'Kir Marchenko \nkir.marchenko@gmail.com'


class ProxyHunter(object):
    def __init__(self, good_proxies='goodproxylist.txt', verbose=False, store=False, timeout=2, threads=200, pages=1):
        self.timeout = timeout
        self.verbose = verbose
        self.goodproxy = good_proxies
        self.threads = threads
        self.max_pages_to_search = pages
        self.store = store

    def print_if_verbose(self, message):
        if self.verbose:
            print message

    def get_links(self):
        untested_proxy = []
        for page in xrange(0, self.max_pages_to_search):
            req = requests.get('https://www.google.com/search?q=+":8080" +":3128" +":80" filetype:txt&start=%s0' % page)
            urls = html.fromstring(req.text).xpath('.//*[@id="ires"]//a/@href')
            for url in urls:
                proxy_file = re.findall("/url\?q=((?!.*webcache)(?:(?:https?|ftp)://|www\.|ftp\.)[^'\r\n]+\.txt)", url)
                proxy_servers = self.get_proxies(proxy_file[0]) if proxy_file else None
                untested_proxy += proxy_servers if proxy_servers else []
        return untested_proxy

    def get_proxies(self, remote_file):
        result = urlparse(remote_file)
        if not result.scheme:
            remote_file = 'http://%s' % remote_file
        if result.scheme == 'ftp':
            return
        self.print_if_verbose("Parse proxy from %s" % (remote_file.split("//", 3)[1]))

        try:
            req = requests.get(remote_file, timeout=self.timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, socket.timeout):
            self.print_if_verbose("Can't connect to %s" % remote_file)
            return
        if not req.ok:
            return
        proxies = re.findall('\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}\s*?[:]\s*?\d{1,5}', req.text)
        self.print_if_verbose("%d Proxies received from %s \n" % (len(proxies), remote_file.split("//", 3)[1]))
        return proxies

    def proxy_is_alive(self, proxy):
        proxies = {
            "http": 'http://%s/' % proxy.replace(' ', '')
        }
        try:
            test_req = requests.get('http://ip-api.com/json', proxies=proxies, timeout=self.timeout)
        except Exception as e:
            return False
        try:
            info = test_req.json()
        except ValueError:
            return False
        if not info['status'] == 'fail':
            place = info['country']
            return proxy, place
        else:
            return False

    def check_proxy(self, proxy_to_check, proxy_list):
        result = self.proxy_is_alive(proxy_to_check)
        if result:
            self.print_if_verbose("%s is alive" % proxy_to_check)
            proxy_list.append(result)
        else:
            self.print_if_verbose("%s is dead" % proxy_to_check)

    def check_proxies_multi_thread(self, proxylist):
        good_proxies = []
        print '%d proxy to check with %d threads. Please wait.' % (len(proxylist),
                                                                   self.threads)
        start_time = datetime.now()
        for proxy in set(proxylist):
            while activeCount() == self.threads:
                sleep(1)
            try:
                thread = Thread(target=self.check_proxy, args=(proxy, good_proxies))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print 'Exception: %s \nActive threads: %d' % (e, activeCount())
        while activeCount() > 1:
            sleep(1)
        finish_time = datetime.now()
        delta = (finish_time - start_time).seconds
        print 'Checked for %d seconds (about %s minutes). ' \
              '%d proxies are good.' % (delta, "{0:.1f}".format(round(float(delta) / 60, 1)), len(good_proxies))
        return good_proxies

    def save_good_proxy_list(self, proxy_list_to_store):
        proxy_list_to_store.sort(key=lambda data: data[1])
        with open(self.goodproxy, 'w') as goodproxy:
            for line in proxy_list_to_store:
                proxy, country = line
                goodproxy.write('%s %s\n' % (proxy, country))
            print "%d fresh proxies saved to %s" % (len(proxy_list_to_store), self.goodproxy)

    def hunt(self):
        return self.get_links()

    def run(self):
        proxies = self.hunt()
        good_proxies = self.check_proxies_multi_thread(proxies)
        if self.store:
            self.save_good_proxy_list(good_proxies)
        return good_proxies


if __name__ == '__main__':
    hunter = ProxyHunter(store=True)
    hunter.run()
