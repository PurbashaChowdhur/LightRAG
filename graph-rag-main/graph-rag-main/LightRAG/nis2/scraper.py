import requests
import subprocess
import time
import os
import json
import re
import logging
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

BASE_URL = "https://www.normattiva.it/"
MAIN_PAGE_URL = "uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2024-09-04;138!vig="
CACHED_STRUCTURE_PATH = "cached_structure.json"
CACHED_ARTICLE_PATH = "./cached_articles/article_{}.json"
ARTICLE_LINK_PATTERN = re.compile('return\sshowArticle\(\'(.*)\'.*\);')
ARTICLE_REF_PATTERN = re.compile('urn:nir:(.*):(.*):(\d{4}[-\d{2}]*)[;~]([art]*\d+)*~*(art\d+)*')


def has_cached_structure():
    """Verify if the structure of the website is cached"""
    return os.path.isfile(CACHED_STRUCTURE_PATH)


def get_cached_structure():
    """Get the cached structure of the website"""
    if has_cached_structure():
        with open(CACHED_STRUCTURE_PATH, "r", encoding='utf-8') as cached_file:
            return json.load(cached_file)
    else:
        return []


def put_cached_structure(structure=None):
    """Put the structure of the website into the cache"""
    if structure is None:
        structure = []
    with open(CACHED_STRUCTURE_PATH, "w", encoding='utf-8') as cached_file:
        json.dump(structure, cached_file, ensure_ascii=False, indent=4)


def is_cached(article_number):
    """Check if an article is already cached"""
    return os.path.isfile(CACHED_ARTICLE_PATH.format(article_number))


def get_cached_article(article_number):
    """Get a cached article by its id"""
    if is_cached(article_number):
        cached_article = CACHED_ARTICLE_PATH.format(article_number)
        with open(cached_article, "r", encoding='utf-8') as cached_file:
            print(f"get_cached_article - article already in cache {cached_article}")
            return json.load(cached_file)
    else:
        return {}


def put_cached_article(article_number, article):
    """Put an article into the cache"""
    with open(CACHED_ARTICLE_PATH.format(article_number), "w", encoding='utf-8') as cached_file:
        json.dump(article, cached_file, ensure_ascii=False, indent=4)


class Nis2Scraper():
    """A scraper that is tailored for https://www.normattiva.it/"""

    def __init__(self, do_not_pressure=True, delay_time=5):
        self.do_not_pressure = do_not_pressure
        # self.header_pattern = re.compile("(.*)\\((.*)\\)\\[(.*)\\]")
        # self.date_pattern = re.compile("(\\d{2}/\\d{2}/\\d{4})")
        self.process = None
        self.is_parsed_page = True
        self.delay_time = delay_time

        self.session = requests.session()
        # self.session.proxies = {'http': 'socks5h://localhost:9050', 'https': 'socks5h://localhost:9050'}
        # self.init_tor_connection()

        self.article_index = {}
        articles = self.get_articles(url=f"{BASE_URL}{MAIN_PAGE_URL}")
        put_cached_structure(articles)

        # Helpful for running webscraping activities anonymously

    def init_tor_connection(self):
        """Initialize the connection to the TOR socket"""
        try:
            self.process = subprocess.Popen(['/opt/homebrew/opt/tor/bin/tor'], shell=True, text=True)
            print('stdout:', self.process.stdout)
            print('stderr:', self.process.stderr)

            # test difference
            not_anonymized_ip = requests.get('http://httpbin.org/ip').text
            print(not_anonymized_ip)
            anonymized_ip = self.session.get('http://httpbin.org/ip').text
            print(anonymized_ip)

            if not_anonymized_ip == anonymized_ip:
                raise Exception('anonymization failed')

        except subprocess.CalledProcessError as e:
            print(f'Error: {e}')
            # fallback to not anonymized version
            self.session.proxies = {}

    def get_page_parsed_content(self, url: str) -> BeautifulSoup:
        """Parse the content of a page"""
        # do not add pressure to the webpage, just wait 10 seconds before returning but only if it's not the first page
        if self.do_not_pressure and not self.is_parsed_page:
            time.sleep(self.delay_time)
        page = self.session.get(url, headers={'User-agent': UserAgent().random})
        self.is_parsed_page = False
        return BeautifulSoup(page.content, "html.parser")

    def get_base_specification_from_ACN(self):
        pass

    def get_attachments(self, url: str) -> list[dict]:
        pass

    def get_articles(self, url: str) -> list[dict]:
        """Get the structure of the website"""
        if has_cached_structure():
            return get_cached_structure()

        articles = []
        main_page = self.get_page_parsed_content(url)
        list_elements = main_page.find("div", {"id": "albero"}).find_all("li")
        for list_element in list_elements:
            a_tag = list_element.find("a")
            if a_tag is not None and a_tag.has_attr('onclick'):
                article_url = ARTICLE_LINK_PATTERN.findall(a_tag['onclick'])
                if len(article_url) > 0:
                    url = f"{BASE_URL}{article_url[0]}"
                    sub_page = self.get_page_parsed_content(url.format(base_url=BASE_URL))
                    article_full_id = sub_page.find(class_="article-num-akn").text if sub_page.find(
                        class_="article-num-akn") is not None else ""
                    try:
                        article_id = int(article_full_id.replace("Art.", ""))
                    except Exception:
                        continue

                    if is_cached(article_number=article_id):
                        continue

                    title = sub_page.find(class_="article-heading-akn").text if sub_page.find(
                        class_="article-heading-akn") is not None else ""
                    content = sub_page.find(class_="art-commi-div-akn").text if sub_page.find(
                        class_="art-commi-div-akn") is not None else ""
                    article_structure = {
                        "full_id": article_full_id,
                        "id": article_id,
                        "content": content,
                        "title": title,
                        "links": [],
                    }

                    articles_ref = sub_page.find_all("a")
                    for article_ref in articles_ref:
                        if article_ref.has_attr('href'):
                            article_url = article_ref.get('href')
                            if article_url.startswith("/"):
                                page_ref = article_url.split("/")[-1].split("?")[-1]
                                # TODO: better to use a regular expression
                                external_ref = ARTICLE_REF_PATTERN.findall(page_ref)
                                if len(external_ref) > 0:
                                    link = {
                                        "law_maker": external_ref[0][0],
                                        "source": external_ref[0][1],
                                        "date": external_ref[0][2],
                                    }
                                    if external_ref[0][3].startswith("art"):
                                        link["article"] = external_ref[0][3]
                                    else:
                                        link["number"] = external_ref[0][3]
                                        if external_ref[0][4].startswith("art"):
                                            link["article"] = external_ref[0][4]
                                    article_structure["links"].append(link)

                    print(article_structure)
                    articles.append(article_structure)
                    put_cached_article(article_number=article_structure["id"], article=article_structure)

        return articles


if __name__ == "__main__":
    scraper = Nis2Scraper(delay_time=5)
