import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
import numpy as np
import re
import logging
import pickle
import json
import datetime
from langchain_neo4j import Neo4jGraph
from whoosh import index
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from keybert import KeyBERT
from settings.global_variables import *

class BM25Baseline:
    def __init__(
            self,
            db:Neo4jGraph, 
            index_dir:str,
            top_k:int,
            logger:logging.Logger = logging.getLogger(__name__)
    ):
        self.db = db
        self.index_dir = index_dir
        self.top_k = top_k
        self.logger = logger

        os.makedirs(self.index_dir, exist_ok=True)

        self.schema = Schema(
            id=ID(stored=True, unique=True), 
            content=TEXT(stored=True)                      
        )

        if not index.exists_in(self.index_dir):
            self.logger.info("Creating a new Whoosh index...")
            self.ix = index.create_in(self.index_dir, self.schema)
            self.index_documents()  
        else:
            self.logger.info("Loading existing Whoosh index...")
            self.ix = index.open_dir(self.index_dir)

        self.keybert_model = KeyBERT("all-MiniLM-L6-v2")

    def index_documents(self):
        """Fetches chunks from Neo4j and indexes them in Whoosh."""
        
        self.logger.info("Fetching chunks from Neo4j...")
        chunks = self.db.query("""
                            MATCH (c:Chunk)
                            RETURN c.id AS id, c.content AS content
                            """)

        self.logger.info(f"Indexing {len(chunks)} chunks into Whoosh...")
        with self.ix.writer() as writer:
            for chunk in chunks:
                writer.add_document(
                    id=chunk["id"],        
                    content=chunk["content"]
                )
        self.logger.info(f"Indexing complete. Indexed {len(chunks)} chunks.")

    def extract_topics(self, question:str):
        """Extracts 3 key topics from a question using KeyBert."""
        
        keywords = self.keybert_model.extract_keywords(question, keyphrase_ngram_range=(1, 2), top_n=3)
        
        return [kw[0] for kw in keywords]

    def retrieve_documents(self, question:str):        
        extracted_topics = self.extract_topics(question)
        search_query = " ".join(extracted_topics)  

        self.logger.info(f"Extracted Topics: {extracted_topics}")
        self.logger.info(f"Using query: '{search_query}' for retrieval.\n")

        retrieved_docs = []
        with self.ix.searcher() as searcher:
            query = QueryParser("content", self.ix.schema).parse(search_query)
            results = searcher.search(query, limit=self.top_k)

            for result in results:
                doc_id = result.get("id", "N/A")
                doc_id = re.sub(r'(\d+)-(\d+)', r'\1(\2)', doc_id)
                doc_id = re.sub(r'(Recital \d+)-(\d+)', r'\1(\2)', doc_id)
                
                retrieved_docs.append({
                    "id": doc_id,  
                    "content": result.get("content", "No content available"),
                    "score": result.score
                })

        return retrieved_docs
    
    def execute_baseline(self, dataset, dataset_name:str):
        for _,(key,item) in enumerate(dataset.items()):
            self.logger.info(f"Question: {item.get('question', 'No question provided')}")
            
            predicted_answer = ''
            references = {
                'articles' : [],
                'recitals' : []
            }

            question = item['question']
            start_time = datetime.datetime.now()
            retrieved_docs = self.retrieve_documents(question)
            end_time = datetime.datetime.now()
            time_difference = end_time - start_time

            for _, doc in enumerate(retrieved_docs):
                if doc['id'].startswith('Recital'):
                    references['recitals'].append(doc['id'])
                else:
                    references['articles'].append(doc['id'])

                predicted_answer += f"- {doc['content']} - {doc['id']}\n"

            target_dir = f"{args.output_dir}/{dataset_name}"
            os.makedirs(target_dir, exist_ok=True)

            with open(f"{args.output_dir}/{dataset_name}/{key}.pkl", 'wb') as pf:
                pickle.dump((predicted_answer, references, time_difference.total_seconds()), pf)

def main(args):
    logging.basicConfig(level=logging.INFO)

    with open(f"{args.questions_dir}/with_ground_truth.json") as f:
        with_ground_truth = json.load(f)

    with open(f"{args.questions_dir}/without_ground_truth.json") as f:
        without_ground_truth = json.load(f)

    bm25 = BM25Baseline(
        db = Neo4jGraph(url = args.neo4j_uri, 
                      username = args.neo4j_username, 
                      password = args.neo4j_password),

        index_dir = args.index_dir,
        top_k = args.top_k
    )

    bm25.execute_baseline(with_ground_truth, "with_ground_truth")
    bm25.execute_baseline(without_ground_truth, "without_ground_truth")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--questions_dir', type=str, default="data/questions")
    parser.add_argument('--output_dir', type=str, default="output/baseline")
    parser.add_argument('--neo4j_uri', type=str, default=NEO4J_URI)
    parser.add_argument('--neo4j_username', type=str, default=NEO4J_USERNAME)
    parser.add_argument('--neo4j_password', type=str, default=NEO4J_PASSWORD)
    parser.add_argument('--index_dir', type=str, default="data/whoosh_index")
    parser.add_argument('--top_k', type=int, default=5)

    args = parser.parse_args()
    main(args)