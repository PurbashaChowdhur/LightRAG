import requests
import re
import nltk
from bs4 import BeautifulSoup

class Chunk:
    """
    The Chunk class is used to store and access the content of a chunk of the AI Act.

    Attributes:
    - chunk_number: the number of the chunk
    - chunk_content: the content of the chunk
    - references: the references of the chunk
    - related_recitals: the related recitals of the chunk
    """
    def __init__(self, chunk_number, chunk_content, references=[], related_recitals=[]):
        self.chunk_number = chunk_number
        self.chunk_content = chunk_content
        self.references = references
        self.related_recitals = related_recitals

class Recital:
    """
    The Recital class is used to store and access the content of a recital of the AI Act.

    Attributes:
    - html_content: the HTML content of the recital
    - soup: the BeautifulSoup object of the recital
    - recital_number: the number of the recital
    - recital_content: the content of the recital

    Methods:
    - set_content(): set the content of the recital
    """
    def __init__(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            self.html_content = response.text
        else:
            print("Failed to download the HTML content.")

        if self.html_content:
            self.soup = BeautifulSoup(self.html_content, 'html.parser')

        match = re.search(r'/recital/(\d+)/', url).group(1).strip()
        if match:
            self.recital_number = match
        else:
            self.recital_number = None
            print("Failed to extract recital number from URL")
        self.recital_content = ""
        self.chunks = []

    def set_content(self) -> str:
        """
        Set the content of the recital.

        Returns:
        - recital_content: the content of the recital
        """
        target_div = self.soup.find('div', class_='et_pb_module et_pb_post_content et_pb_post_content_0_tb_body')
        
        if target_div:
            paragraphs = target_div.find_all('p')
            
            recital_content = ""
            for paragraph in paragraphs:
                text = paragraph.get_text(strip=True)
                recital_content += text + " "

            self.recital_content = recital_content

            return recital_content
        else:
            raise Exception("The specified div element was not found.")
        
    def set_chunks(self) -> list:
        if self.recital_content == "":
            self.set_content()
        self.chunks = nltk.sent_tokenize(self.recital_content)
        return self.chunks

class Annex:
    """
    The Annex class is used to store and access the content of an annex of the AI Act.

    Attributes:
    - html_content: the HTML content of the annex
    - soup: the BeautifulSoup object of the annex
    - annex_number: the number of the annex
    - annex_title: the title of the annex
    - sections: the sections of the annex (if any)
    - chunks: the chunks of the annex

    Methods:
    - set_title(): set the title of the annex
    - set_chunks(): set the chunks of the annex 
    """

    def __init__(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            self.html_content = response.text
        else:
            print("Failed to download the HTML content.")

        if self.html_content:
            self.soup = BeautifulSoup(self.html_content, 'html.parser')

        self.annex_number = ""
        self.annex_title = ""
        self.sections = []
        self.chunks = []

    def set_title(self) -> str:
        """
        Set the title of the annex.

        Returns:
        - annex_title: the title of the annex
        """
        title_div = self.soup.find('div', class_='et_pb_module et_pb_post_title et_pb_post_title_0_tb_body et_pb_bg_layout_light et_pb_text_align_left')
        
        if title_div:
            h1_element = title_div.find('h1', class_='entry-title')
            if h1_element:
                title_text = h1_element.get_text(strip=True)
                _, annex_title = title_text.split(': ', 1)

                self.annex_title = annex_title

                return annex_title
            else:
                raise Exception("The specified h1 element was not found.")

    def set_chunks(self) -> list[Chunk]:
        """
        Set the chunks of the annex.

        Returns:
        - chunks: the chunks of the annex
        """
        target_div = self.soup.find('div', class_='et_pb_module et_pb_post_content et_pb_post_content_0_tb_body')
        
        if target_div:
            paragraphs = target_div.find_all('p')
            sections = target_div.find_all(['h3', 'h5'])

            if sections:
                for idx, section in enumerate(sections):
                    title_text = section.get_text(strip=True)
                    section_title = title_text.split('– ', 1)[1].strip()
                    section_number = idx + 1
                    section_chunks = []
                    
                    chunks = []
                    current_chunk = ""
                    padding_left_text = ""
                    references = []

                    for paragraph in paragraphs:
                        if paragraph.find_previous(['h3', 'h5']) == section:
                            style = paragraph.get('style', '')
                            text = paragraph.get_text(strip=True)
                            hrefs = [a['href'] for a in paragraph.find_all('a', href=True)]
                            href_texts = [f" {a.get_text(strip=True)} " for a in paragraph.find_all('a', href=True)]
                            
                            for href_text in href_texts:
                                text = text.replace(href_text.strip(), href_text)
                            
                            if 'padding-left' in style:
                                padding_left_text += " " + text
                                references.extend(hrefs)
                            else:
                                if current_chunk:
                                    current_chunk += padding_left_text
                                    chunks.append((current_chunk.strip(), references))
                                    current_chunk = ""
                                    padding_left_text = ""
                                    references = []
                                current_chunk = text
                                references = hrefs

                    if current_chunk:
                        current_chunk += padding_left_text
                        chunks.append((current_chunk.strip(), references))

                    filtered_chunks = [(chunk, refs) for chunk, refs in chunks if not chunk.startswith("Related")]

                    cleaned_chunks = [(re.sub(r'^\d+\.\s*|\(\d+\)\s*', '', chunk), refs) for chunk, refs in filtered_chunks]

                    final_chunks = []
                    for idx, (chunk, refs) in enumerate(cleaned_chunks):
                        chunk = chunk.split("Related:")[0].strip()
                        if "Related:Recital" not in chunk:
                            final_chunks.append(Chunk(chunk_number=str(idx+1), chunk_content=chunk, references=refs))
                    
                    section_chunks.extend(final_chunks)

                    self.sections.append({
                        "title": section_title,
                        "number": section_number,
                        "chunks": section_chunks
                    })

                return self.sections

            else:
                chunks = []
                current_chunk = ""
                padding_left_text = ""
                references = []
                
                for paragraph in paragraphs:
                    style = paragraph.get('style', '')
                    text = paragraph.get_text(strip=True)
                    hrefs = [a['href'] for a in paragraph.find_all('a', href=True)]
                    href_texts = [f" {a.get_text(strip=True)} " for a in paragraph.find_all('a', href=True)]
                    
                    for href_text in href_texts:
                        text = text.replace(href_text.strip(), href_text)
                    
                    if 'padding-left' in style:
                        padding_left_text += " " + text
                        references.extend(hrefs)
                    else:
                        if current_chunk:
                            current_chunk += padding_left_text
                            chunks.append((current_chunk.strip(), references))
                            current_chunk = ""
                            padding_left_text = ""
                            references = []
                        current_chunk = text
                        references = hrefs
                
                if current_chunk:
                    current_chunk += padding_left_text
                    chunks.append((current_chunk.strip(), references))

                filtered_chunks = [(chunk, refs) for chunk, refs in chunks if not chunk.startswith("Related")]

                cleaned_chunks = [(re.sub(r'^\d+\.\s*|\(\d+\)\s*', '', chunk), refs) for chunk, refs in filtered_chunks]

                final_chunks = []
                for idx, (chunk, refs) in enumerate(cleaned_chunks):
                    chunk = chunk.split("Related:")[0].strip()
                    if "Related:Recital" not in chunk:
                        final_chunks.append(Chunk(chunk_number=str(idx+1), chunk_content=chunk, references=refs))
                
                self.chunks = final_chunks

                return final_chunks
        else:
            raise Exception("The specified div element was not found.")

class Article:
    """
    The Article class is used to store and access the content of an article of the AI Act.

    Attributes:
    - html_content: the HTML content of the article
    - soup: the BeautifulSoup object of the article
    - entry_into_force: the entry into force of the article
    - article_number: the number of the article
    - article_title: the title of the article
    - chunks: the chunks of the article
    - related_recitals: the related recitals of the article

    Methods:
    - set_entry_into_force(): set the entry into force of the article
    - set_title(): set the title of the article
    - set_chunks(): set the chunks of the article
    - set_related_recitals(): set the related recitals of the article
    """
    def __init__(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            self.html_content = response.text
        else:
            print("Failed to download the HTML content.")

        if self.html_content:
            self.soup = BeautifulSoup(self.html_content, 'html.parser')

        self.entry_into_force = ""
        self.article_number = ""
        self.article_title = ""
        self.chunks = []
        self.related_recitals = []

    def set_entry_into_force(self, chapter_number) -> None:
        """
        Set the entry into force of the article.

        Parameters:
        - chapter_number: the number of the chapter
        """
        if chapter_number == "1" or chapter_number == "2":
                self.entry_into_force = "2 February 2025"
        else:
            if chapter_number == "5" or chapter_number == "7" or chapter_number == "12" or self.article_number == "78":
                self.entry_into_force = "2 August 2025"
            else:
                if self.article_number == "6":
                    self.entry_into_force = "2 August 2026 (2 August 2027 for Point 1)"
                else:
                    self.entry_into_force = "2 August 2026"

    def set_title(self) -> str:
        """
        Set the title of the article.

        Returns:
        - article_title: the title of the article
        """
        title_div = self.soup.find('div', class_='et_pb_module et_pb_post_title et_pb_post_title_0_tb_body et_pb_bg_layout_light et_pb_text_align_left')
        
        if title_div:
            h1_element = title_div.find('h1', class_='entry-title')
            if h1_element:
                title_text = h1_element.get_text(strip=True)
                _, article_title = title_text.split(': ', 1)

                self.article_title = article_title

                return article_title
            else:
                raise Exception("The specified h1 element was not found.")

    def set_chunks(self) -> list[Chunk]:
        """
        Set the chunks of the article.

        Returns:
        - chunks: the chunks of the article
        """
        target_div = self.soup.find('div', class_='et_pb_module et_pb_post_content et_pb_post_content_0_tb_body')
        
        if target_div:
            paragraphs = target_div.find_all('p')
            
            chunks = []
            current_chunk = ""
            padding_left_text = ""
            references = []
            
            for paragraph in paragraphs:
                related_recitals_list = []
                style = paragraph.get('style', '')
                text = paragraph.get_text(strip=True)
                
                hrefs = [a['href'] for a in paragraph.find_all('a', href=True)]
                href_texts = [f" {a.get_text(strip=True)} " for a in paragraph.find_all('a', href=True)]
                
                for href_text in href_texts:
                    text = text.replace(href_text.strip(), href_text)
                
                if 'padding-left' in style:
                    padding_left_text += " " + text
                    references.extend(hrefs)
                else:
                    if current_chunk:
                        current_chunk += padding_left_text
                        chunks.append((current_chunk.strip(), references, related_recitals_list))
                        current_chunk = ""
                        padding_left_text = ""
                        references = []
                    current_chunk = text
                    references = hrefs

                recital_refs = paragraph.find('span', class_='aia-recital-ref')
                if recital_refs:
                    recital_links = recital_refs.find_all('a')
                    for link in recital_links:
                        recital = Recital('https://artificialintelligenceact.eu' + link.get('href') + '/')
                        recital.set_content()
                        related_recitals_list.append(recital)

            if current_chunk:
                current_chunk += padding_left_text
                chunks.append((current_chunk.strip(), references, related_recitals_list))

            cleaned_chunks = [(re.sub(r'^\d+\.\s*|\(\d+\)\s*', '', chunk), refs, recs) for chunk, refs, recs in chunks]

            final_chunks = []
            for idx, (chunk, refs, recs) in enumerate(cleaned_chunks):
                chunk = chunk.split("Related:")[0].strip()
                if "Related: Recital" not in chunk:
                    final_chunks.append(Chunk(chunk_number=str(idx+1), chunk_content=chunk, references=refs, related_recitals=recs))
            
            self.chunks = final_chunks

            return final_chunks
        else:
            raise Exception("The specified div element was not found.")

    def set_related_recitals(self) -> list[Recital]:
        """
        Set the related recitals of the article.

        Returns:
        - related_recitals: the related recitals of the article
        """
        recitals_div = self.soup.find('div', class_='aia-explore-related-list')

        if recitals_div:
            related_recitals = []
            recital_links = recitals_div.find_all('a')
            
            for link in recital_links:
                href = link.get('href')
                recital = Recital(href)
                recital.set_content()

                related_recitals.append(recital)
            
            self.related_recitals = related_recitals
            return related_recitals
        else:
            return []

class Section:
    """
    The Section class is used to store and access the content of a section of the AI Act.

    Attributes:
    - html_content: the HTML content of the section
    - soup: the BeautifulSoup object of the section
    - section_number: the number of the section
    - section_title: the title of the section
    - articles: the articles of the section

    Methods:
    - set_title(): set the title of the section
    - set_articles(): set the articles of the section
    """
    def __init__(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            self.html_content = response.text
        else:
            print("Failed to download the HTML content.")

        if self.html_content:
            self.soup = BeautifulSoup(self.html_content, 'html.parser')

        self.section_number = re.search(r'/section/([0-9\-]+)/', url).group(1)
        self.section_title = ""
        self.articles = []

    def set_title(self) -> str:
        """
        Set the title of the section.

        Returns:
        - section_title: the title of the section
        """
        title_div = self.soup.find('div', class_='et_pb_module et_pb_post_title et_pb_post_title_0_tb_body et_pb_bg_layout_light et_pb_text_align_left')
        
        if title_div:
            h1_element = title_div.find('h1', class_='entry-title')
            if h1_element:
                title_text = h1_element.get_text(strip=True)
                _, section_title = title_text.split(': ', 1)

                self.section_title = section_title

                return section_title
            else:
                raise Exception("The specified h1 element was not found.")

    def set_articles(self, chapter_number) -> list[Article]:
        """
        Set the articles of the section.

        Parameters:
        - chapter_number: the number of the chapter

        Returns:
        - articles: the articles of the section
        """
        related_list_div = self.soup.find('div', class_='aia-explore-related-list')
    
        if related_list_div:
            related_items = related_list_div.find_all('p', class_='related-item')
            
            for item in related_items:
                art = item.get_text(strip=True).split(': ', 1)[0].replace("Article ", "").replace(" ", "")
                article = Article(f"https://artificialintelligenceact.eu/article/{art}/")
                article.article_number = f"{art}"
                article.set_entry_into_force(chapter_number)
                article.set_title()
                article.set_chunks()
                article.set_related_recitals()
                self.articles.append(article) 
            
            return self.articles
        else:
            raise Exception("The specified div element was not found.")

class Chapter:
    """
    The Chapter class is used to store and access the content of a chapter of the AI Act.

    Attributes:
    - url: the URL of the chapter
    - html_content: the HTML content of the chapter
    - soup: the BeautifulSoup object of the chapter
    - chapter_number: the number of the chapter
    - chapter_title: the title of the chapter
    - sections: the sections of the chapter
    - articles: the articles of the chapter

    Methods:
    - set_title(): set the title of the chapter
    - set_sections_and_articles(): set the sections and articles of the chapter
    """
    def __init__(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            self.html_content = response.text
        else:
            print("Failed to download the HTML content.")

        if self.html_content:
            self.soup = BeautifulSoup(self.html_content, 'html.parser')

        self.chapter_number = ""
        self.chapter_title = ""
        self.sections = []
        self.articles = [] 

    def set_title(self) -> str:
        """
        Set the title of the chapter.

        Returns:
        - chapter_title: the title of the chapter
        """
        title_div = self.soup.find('div', class_='et_pb_module et_pb_post_title et_pb_post_title_0_tb_body et_pb_bg_layout_light et_pb_text_align_left')
        
        if title_div:
            h1_element = title_div.find('h1', class_='entry-title')
            if h1_element:
                title_text = h1_element.get_text(strip=True)
                split_title = title_text.split(': ', 1)

                if len(split_title) == 2:
                    _, chapter_title = split_title
                else:
                    chapter_title = split_title[0].split(':')[1].strip()

                self.chapter_title = chapter_title

                return chapter_title
            else:
                raise Exception("The specified h1 element was not found.")

    def set_sections_and_articles(self) -> None:
        """
        Set the sections and articles of the chapter.
        """
        related_list_div = self.soup.find('div', class_='aia-explore-related-list')
    
        if related_list_div:
            related_items = related_list_div.find_all('p', class_='related-item')
            
            for idx, item in enumerate(related_items):
                item_text = item.get_text(strip=True)

                if "Section" in item_text:
                    section = Section(f"https://artificialintelligenceact.eu/section/{self.chapter_number}-{idx+1}/")
                    
                    section.section_number = f"{self.chapter_number}-{idx+1}"
                    section.set_title()
                    section.set_articles(self.chapter_number)
                    self.sections.append(section)
                else:
                    art = item_text.split(': ', 1)[0].replace("Article ", "")
                    
                    article = Article(f"https://artificialintelligenceact.eu/article/{art}/")
                    article.article_number = f"{art}"
                    article.set_entry_into_force(self.chapter_number)
                    article.set_title()
                    article.set_chunks()
                    article.set_related_recitals()
                    self.articles.append(article)
        else:
            raise Exception("The specified div element was not found.")