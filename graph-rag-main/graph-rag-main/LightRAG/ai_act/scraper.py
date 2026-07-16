import os
import json
import requests
from bs4 import BeautifulSoup

ARTICLE_LINK = "https://artificialintelligenceact.eu/article/"
RECITAL_LINK = "https://artificialintelligenceact.eu/recital/"
ANNEX_LINK = "https://artificialintelligenceact.eu/annex/"

CACHED_ARTICLE_PATH = "./cached_docs/article_{}.json"
CACHED_RECITAL_PATH = "./cached_docs/recital_{}.json"
CACHED_ANNEX_PATH = "./cached_docs/annex_{}.json"

class AIActScraper():
    def __init__(self):
        pass

    def get_title(self, soup) -> str:
        title_div = soup.find('div', class_='et_pb_module et_pb_post_title et_pb_post_title_0_tb_body et_pb_bg_layout_light et_pb_text_align_left')
        
        if title_div:
            h1_element = title_div.find('h1', class_='entry-title')
            if h1_element:
                title_text = h1_element.get_text(strip=True)
                _, article_title = title_text.split(': ', 1)

                self.article_title = article_title

                return article_title
            else:
                raise Exception("The specified h1 element was not found.")

    def get_articles(self) -> None:
        for i in range(1,114):
            print(f"Scraping article {i}...")

            article_content = ""
            if not os.path.isfile(CACHED_ARTICLE_PATH.format(i)):
                response = requests.get(ARTICLE_LINK + str(i))
                if response.status_code == 200:
                    html_content = response.text
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        target_div = soup.find('div', class_ = "et_pb_module et_pb_post_content et_pb_post_content_0_tb_body")
                        if target_div:
                            paragraphs = target_div.find_all('p')
                            for paragraph in paragraphs:
                                if paragraph.text:
                                    article_content += paragraph.text + "\n"
                else:
                    raise Exception(f"URL {ARTICLE_LINK + str(i)} is wrong!")
                
                article = {
                    "id": i,
                    "title": self.get_title(soup),
                    "content": article_content,
                    "url" : ARTICLE_LINK + str(i)
                }
                                    
                with open(CACHED_ARTICLE_PATH.format(i), "w", encoding='utf-8') as cached_file:
                    json.dump(article, cached_file, ensure_ascii=False, indent=4)
            else:
                print(f"Article {i} already cached")

    def get_recitals(self) -> None:
        for i in range(1,181):
            print(f"Scraping recital {i}...")

            recital_content = ""
            if not os.path.isfile(CACHED_RECITAL_PATH.format(i)):
                response = requests.get(RECITAL_LINK + str(i))
                if response.status_code == 200:
                    html_content = response.text
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        target_div = soup.find('div', class_ = "et_pb_module et_pb_post_content et_pb_post_content_0_tb_body")
                        if target_div:
                            paragraphs = target_div.find_all('p')
                            for paragraph in paragraphs:
                                if paragraph.text:
                                    recital_content += paragraph.text + "\n"
                else:
                    raise Exception(f"URL {RECITAL_LINK + str(i)} is wrong!")
                
                recital = {
                    "id": i,
                    "content": recital_content,
                    "url" : RECITAL_LINK + str(i)
                }
                                    
                with open(CACHED_RECITAL_PATH.format(i), "w", encoding='utf-8') as cached_file:
                    json.dump(recital, cached_file, ensure_ascii=False, indent=4)
            else:
                print(f"Recital {i} already cached")

    # TODO: fix
    def get_annexes(self) -> None:
        for i in range(1,7):
            print(f"Scraping annex {i}...")

            annex_content = ""
            if not os.path.isfile(CACHED_ANNEX_PATH.format(i)):
                response = requests.get(ANNEX_LINK + str(i))
                if response.status_code == 200:
                    html_content = response.text
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        target_div = soup.find('div', class_ = "et_pb_module et_pb_post_content et_pb_post_content_0_tb_body")
                        if target_div:
                            paragraphs = target_div.find_all('p')
                            for paragraph in paragraphs:
                                if paragraph.text:
                                    annex_content += paragraph.text + "\n"
                else:
                    raise Exception(f"URL {ANNEX_LINK + str(i)} is wrong!")
                
                annex = {
                    "id": i,
                    "content": annex_content,
                }
                                    
                with open(CACHED_ANNEX_PATH.format(i), "w", encoding='utf-8') as cached_file:
                    json.dump(annex, cached_file, ensure_ascii=False, indent=4)
            else:
                print(f"Annex {i} already cached")

if __name__ == '__main__':
    scraper = AIActScraper()
    scraper.get_articles()
    scraper.get_recitals()