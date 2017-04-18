from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import html2text
from backend.scopes import SCOPE_NEWS
import re


def scrape_site(url):
    """
    Scrapes content from a given url
    :param url: The given url
    :return: Content of the website in the "articleBody" itemProp-Tag
    """
    try:
        hdr = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 '
                          'Safari/537.11',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive'}
        req = Request(url, headers=hdr)
        r = urlopen(req).read()
        results = BeautifulSoup(r, 'html.parser').find(itemprop="articleBody")
        to_return = ""
        for thing in results:
            to_return += str(thing)
        replaced = re.sub(r"(< ?br ?/?>){2}", "<br/>", to_return)
        final_replaced = re.sub(r"<p ?>\s?</ ?p>", " ", replaced)
        return final_replaced
    except Exception:
        return None


def format_text(feed):
    """
    Converts a html text to markdown and adds a bottom line to it
    :param feed: Feed to format
    :return: formatted text
    """
    text = html2text.html2text(feed.desc)
    link = feed.link
    scope = feed.scope

    if scope == SCOPE_NEWS:
        text += '\n\n--- \n[Code des Bots](https://github.com/l3d00m/pietsmiet_xposter) | by /u/l3d00m'
    else:
        text = '*[Link zum Post auf pietsmiet.de](' + link + ')*\n\n' + \
               text + '\n\n--- \n[Code des Bots](https://github.com/l3d00m/pietsmiet_xposter) | by /u/l3d00m'

    return text


def smart_truncate(content, link, length=220):
    if not len(content) <= length:
        content = content[:length].rsplit(' ', 1)[0] + '...  '

    return content + "<a href=\"" + link + "\">Auf pietsmiet.de weiterlesen <span>→</span></a>"
