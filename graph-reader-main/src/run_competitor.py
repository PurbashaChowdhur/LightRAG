import numpy as np
import torch
import datetime
import os
import pickle
import argparse
import json
import logging
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from langchain_neo4j import Neo4jGraph
from sentence_transformers.util import cos_sim
from settings.global_variables import *

class SBERT_GPT:
    def __init__(
            self, 
            db:Neo4jGraph,
            embedding_model,
            top_k:int,
            logger:logging.Logger = logging.getLogger(__name__)
    ):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.db = db
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.logger = logger
        
        try:
            self.chunk_embeddings = torch.tensor(np.load("data/chunks/chunk_embeddings.npy")).to(self.device)
            self.chunk_ids = np.load("data/chunks/chunk_ids.npy", allow_pickle=True)
            self.chunk_contents = np.load("data/chunks/chunk_contents.npy", allow_pickle=True)
            self.logger.info(f"Loaded embeddings for {len(self.chunk_contents)} chunks from data/chunks folder.")
        
        except FileNotFoundError:
            self.compute_document_embeddings()

    def compute_document_embeddings(self) -> None:        
        query = "MATCH (c:Chunk) RETURN c.id AS id, c.content AS content"
        chunks = self.db.query(query)
        
        self.chunk_ids = [chunk["id"] for chunk in chunks]
        self.chunk_contents = [chunk["content"] for chunk in chunks]
        self.chunk_embeddings = self.embedding_model.encode(self.chunk_contents, convert_to_tensor=True).to(self.device)

        target_dir = "data/chunks"
        os.makedirs(target_dir, exist_ok=True)

        np.save("data/chunks/chunk_embeddings.npy", self.chunk_embeddings.cpu().numpy())  
        np.save("data/chunks/chunk_ids.npy", self.chunk_ids)
        np.save("data/chunks/chunk_contents.npy", self.chunk_contents)

        self.logger.info(f"Computed and saved embeddings for {len(self.chunk_contents)} chunks in data/chunks folder.")

    def retrieve_documents(self, question:str) -> list[tuple]:        
        question_embedding = self.embedding_model.encode(question, convert_to_tensor=True).to(self.device)
        similarities = cos_sim(question_embedding, self.chunk_embeddings)
        top_indices = similarities.argsort(descending=True)[0][:self.top_k]

        retrieved_chunks = [(self.chunk_ids[i], self.chunk_contents[i]) for i in top_indices]
        return retrieved_chunks  

    def generate_answer_gpt(self, question:str, retrieved_chunks:list[tuple]) -> str:
        context = "\n\n".join([f"Chunk {chunk[0]}: {chunk[1]}" for chunk in retrieved_chunks])

        prompt = f"""You are an AI assistant that answers questions strictly based on provided legal documents.

        **Rules:**
        - Use ONLY the information from the given text.
        - If the retrieved text does not contain the answer, respond: "The provided documents do not contain enough information to answer this question."
        - Cite relevant chunk IDs in your answer.

        **Question:** {question}

        **Retrieved Documents:**
        {context}

        Based on the above retrieved documents, provide a factual and well-structured answer, citing chunk IDs where appropriate.
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that answers questions strictly using provided text."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message

    def answer_question(self, question:str):
        retrieved_chunks = self.retrieve_documents(question, self.top_k)
        answer = self.generate_answer_gpt(question, retrieved_chunks)
        
        retrieved_chunk_ids = [chunk[0] for chunk in retrieved_chunks]
        
        return answer, retrieved_chunk_ids, retrieved_chunks
    
    def execute_competitor(self, dataset, dataset_name:str):
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

            for doc in retrieved_docs:
                if doc[0].startswith('Recital'):
                    references['recitals'].append(doc[0])
                else:
                    references['articles'].append(doc[0])

                predicted_answer += f"- {doc[1]} - {doc[0]}\n"

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

    sbert = SBERT_GPT(
        db = Neo4jGraph(url = args.neo4j_uri, 
                      username = args.neo4j_username, 
                      password = args.neo4j_password),

        embedding_model = SentenceTransformer('all-MiniLM-L6-v2'),
        top_k = args.top_k
    )

    sbert.execute_competitor(with_ground_truth, "with_ground_truth")
    sbert.execute_competitor(without_ground_truth, "without_ground_truth")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--questions_dir', type=str, default="data/questions")
    parser.add_argument('--output_dir', type=str, default="output/competitor")
    parser.add_argument('--neo4j_uri', type=str, default=NEO4J_URI)
    parser.add_argument('--neo4j_username', type=str, default=NEO4J_USERNAME)
    parser.add_argument('--neo4j_password', type=str, default=NEO4J_PASSWORD)
    parser.add_argument('--top_k', type=int, default=5)

    args = parser.parse_args()
    main(args)