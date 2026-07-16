import os
import sys
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import asyncio
import json
import nest_asyncio
import datetime
import pickle
from typing import Literal, List
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete
from lightrag.kg.shared_storage import initialize_pipeline_status

from onto_inspector import OntoInspector

nest_asyncio.apply()

CACHED_ARTICLE_PATH = "./cached_docs/article_{}.json"
CACHED_RECITAL_PATH = "./cached_docs/recital_{}.json"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.join(ROOT_DIR, "rag")

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)
print(f"WorkingDir: {WORKING_DIR}")

os.environ["REDIS_URI"] = "redis://localhost:6379"
os.environ["OPENAI_API_KEY"] = "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"

# neo4j
BATCH_SIZE_NODES = 500
BATCH_SIZE_EDGES = 100
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "Purbasha@geminiairo"
os.environ["NEO4J_MAX_CONNECTION_POOL_SIZE"] = "10"
os.environ["NEO4J_DATABASE"] = "aiactrag_airo"

# milvus
os.environ["MILVUS_URI"] = "http://localhost:19530"
os.environ["MILVUS_USER"] = "root"
os.environ["MILVUS_PASSWORD"] = "Milvus"
os.environ["MILVUS_DB_NAME"] = "default"


def load_ontologies(ontologies=None):
    if ontologies is None:
        ontologies = []

    for ontology in ontologies:
        inspector = OntoInspector(uri=ontology)
        entities, predicates = inspector.entities_and_predicates()

    return entities

class RAG:
    def __init__(
            self,
            chunk_token_size: int = 512,
            llm_model_max_token_size: int = 32768,
            chunk_overlap_token_size: int = 256,
            ontologies=None,
    ):
        if ontologies is None:
            #ontologies = ["ontologies/airo_rdf"]
            ontologies = ["ontologies/ai_act.owl"]

        self.chunk_token_size = chunk_token_size
        self.llm_model_max_token_size = llm_model_max_token_size
        self.chunk_overlap_token_size = chunk_overlap_token_size
        self.entities = load_ontologies(ontologies=ontologies)
        self.rag = asyncio.run(self.__initialize_rag())

    async def load_documents(self, documents: list[str], links: list[str]):
        await self.rag.ainsert(input=documents, file_paths=links)

    async def __initialize_rag(self):
        print("init RAG")

        light_rag = LightRAG(
            working_dir=WORKING_DIR,
            llm_model_func=gpt_4o_mini_complete,
            llm_model_max_token_size=self.llm_model_max_token_size,
            embedding_func=openai_embed,
            chunk_token_size=self.chunk_token_size,
            chunk_overlap_token_size=self.chunk_overlap_token_size,
            kv_storage="JsonKVStorage",
            #graph_storage="NetworkXStorage",
            graph_storage="Neo4JStorage",
            vector_storage="NanoVectorDBStorage",
            doc_status_storage="JsonDocStatusStorage",
            embedding_func_max_async=10,
            llm_model_max_async=10,
            max_parallel_insert=10,
            embedding_cache_config={"enabled": True, "similarity_threshold": 0.9, "use_llm_check": True},
            addon_params={"entity_types": self.entities}
        )

        await light_rag.initialize_storages()
        await initialize_pipeline_status()

        return light_rag
    
    def get_answer(self, question: str):
        print(f"Retrieving answer for question: {question}")
        
        mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = "hybrid"
        answer = self.rag.query(
            question,
            param=QueryParam(mode=mode)
        )

        return answer
    
    def execute(self, question: str):
        documents = []
        sources = []

        for i in range(1, 114):
            cached_article = CACHED_ARTICLE_PATH.format(i)

            with open(cached_article, "r", encoding='utf-8') as cached_file:
                article = json.load(cached_file)
                documents.append(article["content"])
                sources.append(cached_article)
            
        for i in range(1, 181):
            cached_recital = CACHED_RECITAL_PATH.format(i)
            
            with open(cached_recital, "r", encoding='utf-8') as cached_file:
                recital = json.load(cached_file)
                documents.append(recital["content"])
                sources.append(cached_recital)

        asyncio.run(self.load_documents(documents=documents, links=sources))
        response = self.get_answer(question=question)
        print(response)
        return response

if __name__ == "__main__":
    rag = RAG()
    documents = []
    sources = []

    for i in range(1, 114):
        cached_article = CACHED_ARTICLE_PATH.format(i)

        with open(cached_article, "r", encoding='utf-8') as cached_file:
            article = json.load(cached_file)
            documents.append(article["content"])
            sources.append(cached_article)
        
    for i in range(1, 181):
        cached_recital = CACHED_RECITAL_PATH.format(i)
        
        with open(cached_recital, "r", encoding='utf-8') as cached_file:
            recital = json.load(cached_file)
            documents.append(recital["content"])
            sources.append(cached_recital)

    asyncio.run(rag.load_documents(documents=documents, links=sources))

    with open("dataset/with_ground_truth.json", "r", encoding='utf-8') as f:
        with_ground_truth = json.load(f)

        for idx,(key, item) in enumerate(with_ground_truth.items()):
            result = {}
            question = item["question"]
            true_answer = item["answer"]

            start_time = datetime.datetime.now()
            predicted_response = rag.get_answer(question=question)
            end_time = datetime.datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()

            result["question"] = question
            result["true_answer"] = true_answer
            result["predicted_response"] = predicted_response
            result["elapsed_time"] = elapsed_time
            result["idx"] = idx

            pickle_dir = os.path.join(f'results/with ground truth/')
            os.makedirs(pickle_dir, exist_ok=True)
            pickle_file = os.path.join(pickle_dir, f'{key}.pkl')
            with open(pickle_file, 'wb') as pf:
                pickle.dump(result, pf)

            print(predicted_response)

    with open("dataset/without_ground_truth.json", "r", encoding='utf-8') as f:
        without_ground_truth = json.load(f)

        for idx,(key, item) in enumerate(without_ground_truth.items()):
            result = {}
            question = item["question"]

            start_time = datetime.datetime.now()
            predicted_response = rag.get_answer(question=question)
            end_time = datetime.datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()

            result["question"] = question
            result["predicted_response"] = predicted_response
            result["elapsed_time"] = elapsed_time
            result["idx"] = idx

            pickle_dir = os.path.join(f'results/without ground truth/')
            os.makedirs(pickle_dir, exist_ok=True)
            pickle_file = os.path.join(pickle_dir, f'{key}.pkl')
            with open(pickle_file, 'wb') as pf:
                pickle.dump(result, pf)

            print(predicted_response)

    # with open("dataset/with_ground_truth.json", "r", encoding='utf-8') as f:
    #     with_ground_truth = json.load(f)
    #
    #     for idx, (key, item) in enumerate(with_ground_truth.items()):
    #         result = {}
    #         question = item["question"]
    #
    #         start_time = datetime.datetime.now()
    #         predicted_response = rag.get_answer(question=question)
    #         end_time = datetime.datetime.now()
    #         elapsed_time = (end_time - start_time).total_seconds()
    #
    #         result["question"] = question
    #         result["predicted_response"] = predicted_response
    #         result["elapsed_time"] = elapsed_time
    #         result["idx"] = idx
    #
    #         pickle_dir = os.path.join(f'results/with ground truth/')
    #         os.makedirs(pickle_dir, exist_ok=True)
    #         pickle_file = os.path.join(pickle_dir, f'{key}.pkl')
    #         with open(pickle_file, 'wb') as pf:
    #             pickle.dump(result, pf)
    #
    #         print(predicted_response)