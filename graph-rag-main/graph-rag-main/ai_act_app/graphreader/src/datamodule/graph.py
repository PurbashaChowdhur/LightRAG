import sys
import os
import argparse
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils._io import *
from src.utils.neo4j_database import *
from src.model.llm import *
from settings.global_variables import *
from settings.prompts import *
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from tqdm import tqdm
from urllib.parse import urlparse

class GraphLoader():
    def __init__(
            self,
            data_dir:str,
            db:Neo4jGraph,
            gpt:ChatOpenAI,
            embedding_gpt:OpenAIEmbeddings,
            logger:logging.Logger = logging.getLogger(__name__)
    ):
        self.data_dir = data_dir
        self.db = db
        self.gpt = gpt
        self.embedding_gpt = embedding_gpt
        self.logger = logger

    def load_chapters_sections_articles(self):
        for i in tqdm(range(1,14), desc="Loading Chapters, Sections and Articles into Neo4j.."):
            chapter = load_from_pkl(os.path.join(self.data_dir, f"chapters/chapter_{str(i)}.pkl"))

            params_chapter = {"id": chapter.chapter_number,
                            "title": chapter.chapter_title}
            
            query_chapter = add_node(label="Chapter",
                                        properties=params_chapter)
            
            self.db.query(query = query_chapter,
                        params = params_chapter)
            
            if chapter.sections == []:
                for article in chapter.articles:                    
                    params_article = {"id": article.article_number,
                                    "title": article.article_title,
                                    "entry_into_force": article.entry_into_force}
                    
                    query_article = add_node(label="Article",
                                                properties=params_article)
                    
                    self.db.query(query = query_article,
                                params = params_article)
                    
                    self.db.query(query = add_relationship_by_id("Chapter",
                                                        "Article",
                                                        "HAS_ARTICLE",
                                                        chapter.chapter_number,
                                                        article.article_number))
                    
                    for idx, chunk in enumerate(article.chunks):
                        chunk_id = article.article_number + "-" + chunk.chunk_number

                        params_chunk = {"id": chunk_id,
                                        "chunk_number": chunk.chunk_number,
                                        "content": chunk.chunk_content}
                        
                        query_chunk = add_node(label="Chunk",
                                                properties=params_chunk)
                        
                        self.db.query(query = query_chunk,
                                    params = params_chunk)
                        
                        self.db.query(query = add_relationship_by_id("Article",
                                                                "Chunk",
                                                                "HAS_CHUNK",                                                     
                                                                article.article_number,
                                                                chunk_id))
                        
                        if idx > 0:
                            previous_chunk_id = article.article_number + "-" + str(idx)

                            self.db.query(query = add_relationship_chunk_chunk(previous_chunk_id,
                                                                        chunk_id))            
            else:
                for section in chapter.sections:
                    params_section = {"id": section.section_number,
                                    "title": section.section_title}
                    
                    query_section = add_node(label="Section",
                                                properties=params_section)
                    
                    self.db.query(query = query_section,
                                params = params_section)
                    
                    self.db.query(query = add_relationship_by_id("Chapter",
                                                            "Section",
                                                            "HAS_SECTION",
                                                            chapter.chapter_number,
                                                            section.section_number))

                    for article in section.articles:
                        params_article = {"id": article.article_number,
                                        "title": article.article_title,
                                        "entry_into_force": article.entry_into_force}
                        
                        query_article = add_node(label="Article",
                                                    properties=params_article)
                        
                        self.db.query(query = query_article,
                                    params = params_article)
                        
                        self.db.query(query = add_relationship_by_id("Section",
                                                            "Article",
                                                            "HAS_ARTICLE",
                                                            section.section_number,
                                                            article.article_number))
                        
                        for idx, chunk in enumerate(article.chunks):
                            chunk_id = article.article_number + "-" + chunk.chunk_number

                            params_chunk = {"id": chunk_id,
                                            "chunk_number": chunk.chunk_number,
                                            "content": chunk.chunk_content}
                            
                            query_chunk = add_node(label="Chunk",
                                                        properties=params_chunk)
                            
                            self.db.query(query = query_chunk,
                                        params = params_chunk)
                            
                            self.db.query(query = add_relationship_by_id("Article",
                                                                    "Chunk",
                                                                    "HAS_CHUNK",                                                     
                                                                    article.article_number,
                                                                    chunk_id))
                            
                            if idx > 0:
                                previous_chunk_id = article.article_number + "-" + str(idx)
                                
                                self.db.query(query = add_relationship_chunk_chunk(previous_chunk_id,
                                                                            chunk_id))

        self.logger.info(f"Loaded Chapters, Sections and Articles into Neo4j")

    def load_recitals(self):
        for i in tqdm(range(1,181), desc="Loading Recitals into Neo4j.."):
            recital = load_from_pkl(os.path.join(self.data_dir, f"recitals/recital_{str(i)}.pkl"))
            params = {"id" : recital.recital_number, 
                      "content" : recital.recital_content,
                      "embedding": self.embedding_gpt.embed_query(recital.recital_content)}
            
            query = add_node(label="Recital",
                                properties=params)

            self.db.query(query = query,
                     params = params)
            
            for idx, chunk in enumerate(recital.chunks):
                chunk_number = str(idx+1)
                chunk_id = "Recital " + recital.recital_number + "-" + chunk_number

                params_chunk = {"id": chunk_id,
                                "chunk_number": chunk_number,
                                "content": chunk}
                
                query_chunk = add_node(label="Chunk",
                                        properties=params_chunk)
                
                self.db.query(query = query_chunk,
                            params = params_chunk)
                
                self.db.query(query = add_relationship_by_id("Recital",
                                                        "Chunk",
                                                        "HAS_CHUNK",
                                                        recital.recital_number,
                                                        chunk_id))
        self.logger.info(f"Loaded Recitals into Neo4j")

    def load_articles_recitals_relationship(self):
        for i in tqdm(range(1,14), desc="Loading Articles and Recitals Relationship into Neo4j.."):
            chapter = load_from_pkl(os.path.join(self.data_dir, f"chapters/chapter_{str(i)}.pkl"))            
            if chapter.sections == []:
                for article in chapter.articles:
                    if article.related_recitals != []:
                        for related_recital in article.related_recitals:
                            self.db.query(query=add_relationship_article_recital(article.article_number,
                                                                    related_recital.recital_number))
            else:
                for section in chapter.sections:
                    for article in section.articles:
                        if article.related_recitals != []:
                            for related_recital in article.related_recitals:
                                self.db.query(query=add_relationship_article_recital(article.article_number,
                                                                    related_recital.recital_number))
        self.logger.info(f"Loaded Articles and Recitals Relationship into Neo4j")

    def load_chunks_recitals_relationship(self):
        for i in tqdm(range(1,14), desc="Loading Chunks and Recitals Relationship into Neo4j.."):
            chapter = load_from_pkl(os.path.join(self.data_dir, f"chapters/chapter_{str(i)}.pkl"))            
            if chapter.sections == []:
                for article in chapter.articles:
                    for _, chunk in enumerate(article.chunks):
                            chunk_id = article.article_number + "-" + chunk.chunk_number
                            for related_recital in chunk.related_recitals:
                                self.db.query(query=add_relationship_chunk_recital(chunk_id, related_recital.recital_number))
            else:
                for section in chapter.sections:
                    for article in section.articles:
                        for _, chunk in enumerate(article.chunks):
                            chunk_id = article.article_number + "-" + chunk.chunk_number
                            for related_recital in chunk.related_recitals:
                                self.db.query(query=add_relationship_chunk_recital(chunk_id, related_recital.recital_number))
        self.logger.info(f"Loaded Chunks and Recitals Relationship into Neo4j")

    def load_annexes(self):
        for i in tqdm(range(1,14), desc="Loading Annexes into Neo4j.."):
            annex = load_from_pkl(os.path.join(self.data_dir, f"annexes/annex_{str(i)}.pkl"))

            params = {"id" : annex.annex_number,
                    "title" : annex.annex_title}
            
            query = add_node(label="Annex",
                                properties=params)
            
            self.db.query(query = query,
                        params = params)
                        
            if annex.sections != []:
                for section in annex.sections:
                    section_id = "Annex " + annex.annex_number + "-" + str(section['number'])

                    params_section = {"id": section_id,
                                    "title" : section['title']}
                    
                    query_section = add_node(label="Section",
                                            properties=params_section)
                    
                    self.db.query(query = query_section,
                            params = params_section)
                    
                    self.db.query(query = add_relationship_by_id("Annex",
                                                        "Section",
                                                        "HAS_SECTION",
                                                        annex.annex_number,
                                                        section_id))
                    
                    for idx, chunk in enumerate(section['chunks']):
                        chunk_id = section_id + "-" + chunk.chunk_number

                        params_chunk = {"id": chunk_id,
                                        "chunk_number": chunk.chunk_number,
                                        "content": chunk.chunk_content}
                    
                        query_chunk = add_node(label="Chunk",
                                                properties=params_chunk)
                        
                        self.db.query(query = query_chunk,
                                params = params_chunk)
                        
                        self.db.query(query = add_relationship_by_id("Section",
                                                                "Chunk",
                                                                "HAS_CHUNK",
                                                                section_id,
                                                                chunk_id))
                        
                        if idx > 0:
                            self.db.query(query = add_relationship_chunk_chunk("Annex " + annex.annex_number + "-" + str(idx),
                                                                        chunk_id))
            else:
                for idx, chunk in enumerate(annex.chunks):
                        chunk_id = "Annex " + annex.annex_number + "-" + chunk.chunk_number

                        params_chunk = {"id": chunk_id,
                                        "chunk_number": chunk.chunk_number,
                                        "content": chunk.chunk_content}
                        
                        query_chunk = add_node(label="Chunk",
                                                properties=params_chunk)
                        
                        self.db.query(query = query_chunk,
                                params = params_chunk)
                        
                        self.db.query(query = add_relationship_by_id("Annex",
                                                                "Chunk",
                                                                "HAS_CHUNK",
                                                                annex.annex_number,
                                                                chunk_id))
                        
                        if idx > 0:
                                self.db.query(query = add_relationship_chunk_chunk("Annex " + annex.annex_number + "-" + str(idx),
                                                                        chunk_id))
        self.logger.info(f"Loaded Annexes into Neo4j")

    def load_references(self):
        for i in tqdm(range(1,14), desc="Loading References into Neo4j.."):
            chapter = load_from_pkl(os.path.join(self.data_dir, f"chapters/chapter_{str(i)}.pkl"))            
            if chapter.sections == []:
                for article in chapter.articles:                    
                    for _, chunk in enumerate(article.chunks):
                        chunk_id = article.article_number + "-" + chunk.chunk_number
                        for ref in chunk.references:
                            if "recital" in ref:
                                continue
                            res = urlparse(ref).path.lstrip('/').split("/")
                            name = res[0]
                            number = res[1]
                            match name:
                                case "article":
                                    self.db.query(query = add_relationship_by_id("Chunk",
                                                                        "Article",
                                                                        "HAS_REFERENCE",
                                                                        chunk_id,
                                                                        number))
                                case "section":
                                    self.db.query(query = add_relationship_by_id("Chunk",
                                                                        "Section",
                                                                        "HAS_REFERENCE",
                                                                        chunk_id,
                                                                        number))
                                    
                                case "chapter":
                                    self.db.query(query = add_relationship_by_id("Chunk",
                                                                        "Chapter",
                                                                        "HAS_REFERENCE",
                                                                        chunk_id,
                                                                        number))
                                    
                                case "annex":
                                    self.db.query(query = add_relationship_by_id("Chunk",
                                                                        "Annex",
                                                                        "HAS_REFERENCE",
                                                                        chunk_id,
                                                                        number))
            else:
                for section in chapter.sections:
                    for article in section.articles:                        
                        for _, chunk in enumerate(article.chunks):
                            chunk_id = article.article_number + "-" + chunk.chunk_number
                            for ref in chunk.references:
                                if "recital" in ref:
                                    continue
                                res = urlparse(ref).path.lstrip('/').split("/")
                                name = res[0]
                                number = res[1]
                                match name:
                                    case "article":
                                        self.db.query(query = add_relationship_by_id("Chunk",
                                                                            "Article",
                                                                            "HAS_REFERENCE",
                                                                            chunk_id,
                                                                            number))
                                    case "section":
                                        self.db.query(query = add_relationship_by_id("Chunk",
                                                                            "Section",
                                                                            "HAS_REFERENCE",
                                                                            chunk_id,
                                                                            number))
                                        
                                    case "chapter":
                                        self.db.query(query = add_relationship_by_id("Chunk",
                                                                            "Chapter",
                                                                            "HAS_REFERENCE",
                                                                            chunk_id,
                                                                            number))
                                        
                                    case "annex":
                                        self.db.query(query = add_relationship_by_id("Chunk",
                                                                            "Annex",
                                                                            "HAS_REFERENCE",
                                                                            chunk_id,
                                                                            number))
        self.logger.info(f"Loaded References into Neo4j")

    def load_atomic_facts_key_elements(self):
        gpt_extraction = self.gpt.with_structured_output(Extraction)
        prompt_extraction = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    key_atomic_extraction,
                ),
                (
                    "human",
                    "{input}",
                ),
            ]
        )

        chain_extraction = prompt_extraction | gpt_extraction

        for i in tqdm(range(1,14), desc="Loading AtomicFacts and KeyElements into Neo4j.."):
            chapter = load_from_pkl(os.path.join(self.data_dir, f"chapters/chapter_{str(i)}.pkl"))            
            if chapter.sections == []:
                for article in chapter.articles:
                    for chunk_number, chunk in enumerate(article.chunks):
                        response = chain_extraction.invoke({"input":chunk.chunk_content})
                        
                        for index, elem in enumerate(response.atomic_facts):
                            atomic_fact = elem.atomic_fact
                            key_elements = elem.key_elements

                            atomic_fact_id = f"{article.article_number}-{chunk_number+1}-{index+1}"
                            chunk_id = article.article_number + "-" + str(chunk_number+1)

                            params_atomic_fact = {"id":atomic_fact_id,
                                                "content": atomic_fact,
                                                "embedding": self.embedding_gpt.embed_query(atomic_fact)}
                            
                            query_atomic_fact = add_node(label="AtomicFact",
                                                        properties=params_atomic_fact)

                            self.db.query(query = query_atomic_fact,
                                    params = params_atomic_fact)
                            
                            self.db.query(query = add_relationship_chunk_atomic_fact(chunk_id,
                                                                                str(chunk_number+1),
                                                                                atomic_fact_id),
                                    params={})
                            
                            for key_element in key_elements:
                                if "Article" in key_element or "Section" in key_element or "Chapter" in key_element or "Annex" in key_element or "paragraph" in key_element or "2025" in key_element or "2026" in key_element or "Regulation" in key_element:
                                    continue

                                embedding = self.embedding_gpt.embed_query(key_element)
                            
                                result_check = self.db.query(query = check_key_elements(embedding))
                                
                                if result_check == []:
                                    params_key_element = {"content": key_element,
                                                        "embedding" : embedding}
                                    query_key_element = add_node(label="KeyElement",
                                                                properties=params_key_element)
                                    
                                    self.db.query(query = query_key_element,
                                            params = params_key_element)
                                    
                                    self.db.query(query = add_relationship_atomic_fact_key_elements(atomic_fact_id, key_element),
                                            params={})
                                else:
                                    for elem in result_check:
                                        self.db.query(query = add_relationship_atomic_fact_key_elements(atomic_fact_id, elem['key_element']),
                                                params={})    
                break
            else:
                for section in chapter.sections:
                    for article in section.articles:
                        for chunk_number, chunk in enumerate(article.chunks):
                            response = chain_extraction.invoke({"input":chunk.chunk_content})

                            for index, elem in enumerate(response.atomic_facts):
                                atomic_fact = elem.atomic_fact
                                key_elements = elem.key_elements

                                atomic_fact_id = f"{article.article_number}-{chunk_number+1}-{index+1}"
                                chunk_id = article.article_number + "-" + str(chunk_number+1)

                                params_atomic_fact = {"id":atomic_fact_id,
                                                    "content": atomic_fact}
                                
                                query_atomic_fact = add_node(label="AtomicFact",
                                                            properties=params_atomic_fact)

                                self.db.query(query = query_atomic_fact,
                                        params = params_atomic_fact)
                                
                                self.db.query(query = add_relationship_chunk_atomic_fact(chunk_id,
                                                                                    str(chunk_number+1),
                                                                                    atomic_fact_id),
                                        params={})
                                
                                for key_element in key_elements:
                                    if "Article" in key_element or "Section" in key_element or "Chapter" in key_element or "Annex" in key_element or "paragraph" in key_element or "2025" in key_element or "2026" in key_element or "Regulation" in key_element or "point" in key_element:
                                        continue

                                    embedding = self.embedding_gpt.embed_query(key_element)
                                    
                                    result_check = self.db.query(query = check_key_elements(embedding))
                                    
                                    if result_check == []:
                                        params_key_element = {"content": key_element,
                                                            "embedding" : embedding}
                                        query_key_element = add_node(label="KeyElement",
                                                                    properties=params_key_element)
                                        
                                        self.db.query(query = query_key_element,
                                                params = params_key_element)
                                        
                                        self.db.query(query = add_relationship_atomic_fact_key_elements(atomic_fact_id, key_element),
                                                params={})
                                    else:
                                        for elem in result_check:
                                            self.db.query(query = add_relationship_atomic_fact_key_elements(atomic_fact_id, elem['key_element']),
                                                    params={})     
        self.logger.info(f"Loaded Atomic Facts and Key Elements into Neo4j")

    def check_consistency(self):
        for query in check_db_correctness():
            if self.db.query(query = query) != []:
                raise Exception(f"Database is not consistent. Query: {query} returned non-empty result.")

def main(args: argparse.Namespace):
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    graph_loader = GraphLoader(
        data_dir = args.data_dir,
        db = Neo4jGraph(url = args.neo4j_uri, 
                        username = args.neo4j_username, 
                        password= args.neo4j_password,
                        database=args.neo4j_database,
        ),

        gpt = ChatOpenAI(model=MODEL,
                        api_key=args.openai_api_key),

        embedding_gpt = OpenAIEmbeddings(model = EMBEDDING_OPENAI,
                                    api_key = args.openai_api_key,
                                    dimensions = EMBEDDING_DIMENSION) 
    )

    # graph_loader.load_chapters_sections_articles()
    # graph_loader.load_recitals()
    # graph_loader.load_articles_recitals_relationship()
    # graph_loader.load_chunks_recitals_relationship()
    # graph_loader.load_annexes()
    # graph_loader.load_references()
    graph_loader.load_atomic_facts_key_elements()
    graph_loader.check_consistency()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--data_dir', type=str, default="data/ai act")
    parser.add_argument('--neo4j_uri', type=str, default=NEO4J_URI)
    parser.add_argument('--neo4j_username', type=str, default=NEO4J_USERNAME)
    parser.add_argument('--neo4j_password', type=str, default=NEO4J_PASSWORD)
    parser.add_argument('--neo4j_database', type=str, default=NEO4J_DATABASE)
    parser.add_argument('--openai_api_key', type=str, default=OPENAI_API_KEY)    

    args = parser.parse_args()
    main(args)