# pyproxyhunter
Python proxy hunter is a tool that will help you to get quickly a number of free and fast proxy servers.

##Usage:
### From CLI to easily hunt proxies and  save them to output.txt file:
```bash
user@localhost:~/pyproxyhunter$ python pyproxyhunter.py 
6236 proxy to check with 200 threads. Please wait.
Checked for 99 seconds (about 1.6 minutes). 777 proxies are good.
777 fresh proxies saved to output.txt
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
777 output.txt
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
9132 proxy to check with 150 threads. Please wait.
Checked for 187 seconds (about 3.1 minutes). 837 proxies are good.
[u'217.20.83.130:3128', u'37.228.89.210:80', u'79.120.72.222:3128', u'31.131.251.102:8080', u'90.154.127.19:8000', 
u'95.215.71.46:3128', u'93.88.143.100:3128', u'94.230.120.195:3128', u'188.40.62.138:80', u'85.143.24.70:80', 
u'85.198.106.174:3128', u'37.143.8.59:81', u'217.20.83.130:3128', u'85.143.24.70:80', u'178.210.47.239:3128', 
u'5.53.16.183:8080']
```

In case of any questions you can contact me via kir.marchenko@gmail.com

