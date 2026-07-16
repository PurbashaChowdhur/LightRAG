import os
import json
import requests
from bs4 import BeautifulSoup

# CHAPTER_LINK = "https://artificialintelligenceact.eu/chapter/"
# SECTION_LINK = "https://artificialintelligenceact.eu/section/"
ARTICLE_LINK = "https://artificialintelligenceact.eu/article/"
RECITAL_LINK = "https://artificialintelligenceact.eu/recital/"
ANNEX_LINK = "https://artificialintelligenceact.eu/annex/"

# CACHED_CHAPTER_PATH1 = "./cached_docs1/chapter_{}.json"
# CACHED_SECTION_PATH1 = "./cached_docs1/section_{}.json"
CACHED_ARTICLE_PATH1 = "./cached_docs1/article_{}.json"
CACHED_RECITAL_PATH1 = "./cached_docs1/recital_{}.json"
CACHED_ANNEX_PATH1 = "./cached_docs1/annex_{}.json"


class AIActScraper():
    def __init__(self):
        pass

    def get_title(self, soup) -> str:
        title_div = soup.find('div',
                              class_='et_pb_module et_pb_post_title et_pb_post_title_0_tb_body et_pb_bg_layout_light '
                                     'et_pb_text_align_left')

        if title_div:
            h1_element = title_div.find('h1', class_='entry-title')
            if h1_element:
                title_text = h1_element.get_text(strip=True)
                _, article_title = title_text.split(': ', 1)

                self.article_title = article_title

                return article_title
            else:
                raise Exception("The specified h1 element was not found.")

 #   def get_chapter(self, soup) -> str:
#        chapter_div = soup.find('div',
#                              class_='et_pb_with_border et_pb_module et_pb_text et_pb_text_4_tb_body et_pb_text_align_left et_pb_bg_layout_light')

#        if chapter_div:
#            h2_element = chapter_div.find('h2', class_='entry-title')
#            if h2_element:
#                title_text = h2_element.get_text(strip=True)
#                _, chapter_title = title_text.split(': ', 1)

#                self.chapter_title = chapter_title

#                return chapter_title
#            else:
#                return "Unknown chapter"

    #def get_section(self, soup) -> str:
        #section_div = soup.find('div',
                               # class_='et_pb_with_border et_pb_module et_pb_text et_pb_text_4_tb_body et_pb_text_align_left et_pb_bg_layout_light')

        #if section_div:
            #h3_element = section_div.find('h3', class_='entry-title')
            #if h3_element:
                #title_text = h3_element.get_text(strip=True)
                #_, section_title = title_text.split(': ', 1)

                #self.section_title = section_title

                #return section_title
            #else:
                #return "no section"

    def get_articles(self) -> None:
        for i in range(1, 114):
            print(f"Scraping article {i}...")

            article_content = ""
            if not os.path.isfile(CACHED_ARTICLE_PATH1.format(i)):
                response = requests.get(ARTICLE_LINK + str(i))
                if response.status_code == 200:
                    html_content = response.text
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        target_div = soup.find('div',
                                               class_="et_pb_module et_pb_post_content et_pb_post_content_0_tb_body")
                        if target_div:
                            paragraphs = target_div.find_all('p')
                            for paragraph in paragraphs:
                                if paragraph.text:
                                    article_content += paragraph.text + "\n"


                else:
                    raise Exception(f"URL {ARTICLE_LINK + str(i)} is wrong!")

                article = {
                    "id": i,
                    #"chapter": self.get_chapter(soup),
                    #"section": self.get_section(soup),
                    "title": self.get_title(soup),
                    "content": article_content,
                }

                with open(CACHED_ARTICLE_PATH1.format(i), "w", encoding='utf-8') as cached_file:
                    json.dump(article, cached_file, ensure_ascii=False, indent=4)
            else:
                print(f"Article {i} already cached")

    def get_recitals(self) -> None:
        for i in range(1, 181):
            print(f"Scraping recital {i}...")

            recital_content = ""
            if not os.path.isfile(CACHED_RECITAL_PATH1.format(i)):
                response = requests.get(RECITAL_LINK + str(i))
                if response.status_code == 200:
                    html_content = response.text
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        target_div = soup.find('div',
                                               class_="et_pb_module et_pb_post_content et_pb_post_content_0_tb_body")
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
                }

                with open(CACHED_RECITAL_PATH1.format(i), "w", encoding='utf-8') as cached_file:
                    json.dump(recital, cached_file, ensure_ascii=False, indent=4)
            else:
                print(f"Recital {i} already cached")

    # TODO: fix
    def get_annexes(self) -> None:
        for i in range(1, 7):
            print(f"Scraping annex {i}...")

            annex_content = ""
            if not os.path.isfile(CACHED_ANNEX_PATH1.format(i)):
                response = requests.get(ANNEX_LINK + str(i))
                if response.status_code == 200:
                    html_content = response.text
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        target_div = soup.find('div',
                                               class_="et_pb_module et_pb_post_content et_pb_post_content_0_tb_body")
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

                with open(CACHED_ANNEX_PATH1.format(i), "w", encoding='utf-8') as cached_file:
                    json.dump(annex, cached_file, ensure_ascii=False, indent=4)
            else:
                print(f"Annex {i} already cached")


if __name__ == '__main__':
    scraper1 = AIActScraper()
    scraper1.get_articles()
    scraper1.get_recitals()
