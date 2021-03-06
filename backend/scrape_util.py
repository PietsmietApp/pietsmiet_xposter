from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import html2text
from backend.log_util import log
import re


def scrape_site(url):
    """
    Scrapes content from a given url
    :param url: The given url
    :return: Content of the website in the "articleBody" itemProp-Tag
    """
    # Open the site with specific headers so we don't get a 403 / 404
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

    # Find all paragraphs in the "<article>" tag
    results = BeautifulSoup(r, 'html.parser').find("article").find_all("p")

    # Combine all non empty paragraphs into one string
    result = ""
    for thing in results:
        if not str(thing.get_text()).isspace():
            result += str(thing)

    # Additional whitespace removal:        
    # replace two linebreaks with one
    replaced = re.sub(r"(< ?br ?/?>){2}", "<br/>", result)
    # delete a linebreak if it's followed by a paragraph ending
    to_return = re.sub(r"< ?br ?/?>\s?</ ?p>", "</p>", replaced)
    return to_return


def format_text(feed):
    """
    Converts a html text to markdown and adds a bottom line to it
    :param feed: Feed to format
    :return: formatted text
    """
    text = html2text.html2text(feed.desc)
    link = feed.link

    text = '[Link zum PietSmiet.de-Artikel](' + link + ')\n\n' + \
           text + '\n\n--- \n[Code](https://github.com/PietsmietApp/pietsmiet_xposter) | ' + \
           '*Auch als Push-Benachrichtigung in der [Community App für Pietsmiet](' \
           'https://play.google.com/store/apps/details?id=de.pscom.pietsmiet&referrer=utm_source%3Dreddit' \
           '%26utm_medium%3Duploadplan)* '

    return text


def smart_truncate(feed, length=220):
    content = feed.desc
    if not len(content) <= length:
        content = feed.desc[:length].rsplit(' ', 1)[0] + '...  '

    return content + "<a href=\"" + feed.link + "\">Auf pietsmiet.de weiterlesen →</a>"
