# pyproxyhunter (python proxyhunter)
Python proxy hunter is a tool that will help you to get quickly a number of free and fast proxy servers.
It hunt proxy servers via google search, so you will have fresh results every time you use this software.
You can save fast and free proxy servers sorted by country to the text file, or import this module to your python program.

##Usage:
### Install requirements
```pip install -r requirements.txt```
I hope soon you'll need just to `pip install pyproxyhunter`
### From CLI to easily hunt proxies and  save them to output.txt file:
```bash
user@localhost:~/pyproxyhunter$ python pyproxyhunter.py 
Proxy servers would be saved to /home/user/pyproxyhunter/output.txt.
12046 proxy to check with 500 threads. Please wait.
Time: 0:01:02 Progress: 100%                                                                                                                                    
284 proxies are good.
284 fresh proxies saved to /home/user/pyproxyhunter/output.txt
user@localhost:~/pyproxyhunter$ head output.txt 
193.194.69.36:3128      Algeria
200.70.56.204:3128      Argentina
190.228.33.114:8080     Argentina
89.249.207.65:3128      Armenia
203.37.37.143:80        Australia
195.34.146.175:80       Austria
103.13.133.202:8080     Bangladesh
103.13.133.198:8080     Bangladesh
189.113.135.230:8080    Brazil
177.44.136.226:3128     Brazil
user@localhost:~/pyproxyhunter$ wc -l output.txt
284 output.txt
```
### Importing module to your own project:
```python
from pyproxyhunter import ProxyHunter

hunter = ProxyHunter(pages=2, timeout=3, threads=150)

proxy_servers = hunter.hunt()

russian_proxies = [proxy.server for proxy in proxy_servers if proxy.country == 'Russia']

print russian_proxies
```
You'll get the following output:
```
13396 proxy to check with 150 threads. Please wait.
Time: 0:04:33 Progress: 100%                                                                                                                                    
428 proxies are good.
[u'85.143.24.70:80', u'82.200.81.233:80', u'78.36.152.6:8080', u'85.143.24.70:80', u'185.12.94.236:4444', 
u'77.73.236.18:3128', u'84.242.242.182:8080', u'193.238.50.62:8080', u'46.8.49.26:10000', u'77.73.110.222:3128', 
u'80.253.28.174:8080', u'83.239.227.245:8080', u'46.21.68.1:8080', u'80.240.104.241:8000', u'83.69.209.146:8080', 
u'185.12.94.236:4444', u'5.53.16.183:8080', u'217.21.220.156:8080', u'77.233.11.50:80', u'85.143.24.70:80', 
u'178.49.228.101:3128']
```

In case of any questions you can contact me via kir.marchenko@gmail.com
