# VERSION: 0.1
# AUTHORS: KR@justfoolingaround (https://github.com/justfoolingaround)

import re
from urllib.parse import quote, unquote

import httpx
import lxml.html as htmlparser

ENGINE_NAME = "nyaa[sukebei]"
SITE_URL = "https://sukebei.nyaa.si"

SIZES = {
    'Gi': 0x40000000,
    'Mi': 0x100000,
    'Ki': 0x400,
}

CATEGORIES = { 
    'All': '0_0',
    'Art: *': '1_0',
    'Art: Anime': '1_1',
    'Art: Doujinshi': '1_2',
    'Art: Games': '1_3',
    'Art: Manga': '1_4',
    'Art: Pictures': '1_5',
    'Real Life: *': '2_0',
    'Real Life: Photobooks and Pictures': '2_1',
    'Real Life: Videos': '2_2',
}

def parse_size(sukebei_nyaa_size):
    size_match = re.search('([\d.]+) ([GMK]i)?B', sukebei_nyaa_size)

    if not size_match:
        return 0

    return int(SIZES.get(size_match.group(2), 1) * float(size_match.group(1)))

def sanitize_stdout_data(txt: str, *, sanitation_txts='|'):
    """
    Sanitation of strings like '|' which might cause issues in the stdout stream read.    
    """
    return ''.join(t if t.isascii() and not t in sanitation_txts else quote(t) for t in txt)

def to_stdout(content: dict, index: int):
    """
    Formatting the content and sending that data to the stdout.
    """
    return print('{magnet}|{index}. {category} - {name}|{size}|{seeders}|{leechers}|{engine}|{url}'.format(**content, engine=ENGINE_NAME, index=index))
        
def generate_page_results(html_element):
    for tr in html_element.cssselect('tr[class]'):
        cat, name, links, size, date, seed, leech, _ = tr.cssselect('td')

        *_, magnet = (_.get('href') for _ in links.cssselect('a[href]'))
        content_identifier = name.cssselect('a[href]')[0]

        yield {
            'category': sanitize_stdout_data(' '.join(a.get('title') for a in cat.cssselect('a[href]'))).strip(),
            'name': sanitize_stdout_data(content_identifier.text_content()).strip(),
            'magnet': sanitize_stdout_data(magnet),
            'size': parse_size(size.text_content()),
            'seeders': seed.text_content(),
            'leechers': leech.text_content(),
            'url': SITE_URL + content_identifier.get('href', ''),
        }

class qBittorrentExtension:
    """
    A base class for qBittorrent extensions.
    """
    url = None
    name = None
    supported_categories = {}
    
    def search(self, what, cat):
        raise NotImplementedError()

class sukebei(qBittorrentExtension):
    """
    An actually decent Sukebei extension for qBittorrent.
    """
    
    url = "https://sukebei.nyaa.si"
    name = "sukebei"
    supported_categories = {
            'all': '0_0',
            'anime': '1_1',
            'books': '1_4',
            'games': '1_2',
            'pictures': '1_5',
        }
        
    def __init__(self):
        """
        Initializing the session that is going to be used in this extension.
        """
        self.session = httpx.Client()

    def generate_results(self, query, cat):
        """
        A generator that will provide you search results continously until exhaustion so that the search results look juicier.
        """
        sukebei_nyaa_page = htmlparser.fromstring(self.session.get(self.url, params={'c': cat, 'q': query}).text)
        page = 1

        while not bool(sukebei_nyaa_page.cssselect('.pagination > li:last-of-type.disabled')):
            yield from generate_page_results(sukebei_nyaa_page)
            
            sukebei_nyaa_page = htmlparser.fromstring(self.session.get(self.url, params={'c': cat, 'q': query, 'p': page}).text)
            page += 1

        
    def search(self, what, cat='all'):
        """
        The main search function.
        """
        for index, content in enumerate(self.generate_results(unquote(what), self.supported_categories.get(cat)), 1):
            to_stdout(content, index)

if __name__ == '__main__':
    """
    Debug mode; run from cli with a search query for checking/testing/debugging.
    """
    import sys
    sukebei().search(' '.join(sys.argv[1:]))
