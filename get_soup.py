import requests
from bs4 import BeautifulSoup
import urllib3


# demo stuff
def get_soup(url):
    # fill with your own proxy settings here,
    # in case of cloudflare blocking your requests

    headers = {
        "referer": "https://www.hltv.org/stats",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    cookies = {"hltvTimeZone": "Europe/Copenhagen"}

    return BeautifulSoup(
        requests.get(url, headers=headers, cookies=cookies).text, "lxml"
    )
