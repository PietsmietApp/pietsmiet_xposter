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
        # replace two linebreaks with one
        replaced = re.sub(r"(< ?br ?/?>){2}", "<br/>", to_return)
        # delete a linebreak if it's followed by a paragraph ending
        replaced2 = re.sub(r"< ?br ?/?>\s?</ ?p>", "</p>", to_return)
        # delete empty paragraphs
        final_replaced = re.sub(r"<p ?>\s?</ ?p>", " ", replaced2)
        return final_replaced
    except Exception:
        return None


def format_text(feed):
    """
    Converts a html text to markdown and adds a bottom line to it
    :param feed: Feed to format
    :return: formatted text
    """
    m_text = html2text.html2text(feed.desc)
    link = feed.link
    scope = feed.scope
    
    text = replaced = re.sub(r" \*\*", "** ", m_text)

    # if scope == SCOPE_NEWS:
        # text += '\n\n--- \n[Code des Bots](https://github.com/l3d00m/pietsmiet_xposter) | by /u/l3d00m'
    # else:
    text = '[Link zum PietSmiet.de-Artikel](' + link + ')\n\n' + \
            text + '\n\n--- \n[Code des Bots](https://github.com/l3d00m/pietsmiet_xposter) | by /u/l3d00m  ' + \
            '\n\n *Auch als Push-Benachrichtigung in der [Community App für Pietsmiet](https://play.google.com/store/apps/details?id=de.pscom.pietsmiet&referrer=utm_source%3Dreddit%26utm_medium%3Duploadplan)*'

    return text


def smart_truncate(feed, length=220):
    if not len(feed.desc) <= length:
        content = feed.desc[:length].rsplit(' ', 1)[0] + '...  '

    return content + "<a href=\"" + feed.link + "\">Auf pietsmiet.de weiterlesen →</a>"
