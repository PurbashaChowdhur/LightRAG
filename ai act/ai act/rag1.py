import os
import asyncio
import json
import nest_asyncio
from typing import Literal
from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.llm.llama_index_impl import llama_index_embed, llama_index_complete
from lightrag.kg.shared_storage import initialize_pipeline_status

nest_asyncio.apply()

CACHED_ARTICLE_PATH = "./cached_docs/article_{}.json"
CACHED_RECITAL_PATH = "./cached_docs/recital_{}.json"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.join(ROOT_DIR, "rag")

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)
print(f"WorkingDir: {WORKING_DIR}")

os.environ["REDIS_URI"] = ""
os.environ["OLLAMA_API_KEY"] = ""
# neo4j
BATCH_SIZE_NODES = 500
BATCH_SIZE_EDGES = 400
os.environ["NEO4J_URI"] = ""
os.environ["NEO4J_USERNAME"] = ""
os.environ["NEO4J_PASSWORD"] = ""
os.environ["NEO4J_MAX_CONNECTION_POOL_SIZE"] = ""
os.environ["NEO4J_DATABASE"] = ""


# milvus
# os.environ["MILVUS_URI"] = ""
# os.environ["MILVUS_USER"] = ""
# os.environ["MILVUS_PASSWORD"] = ""
# os.environ["MILVUS_DB_NAME"] = ""
class OllamaEmbedWrapper:
    def __init__(self, embedding_dim=1536):
        self.embedding_dim = embedding_dim

    def __call__(self, texts, **kwargs):
        return ollama_embed(texts, **kwargs)

class RAG:
    def __init__(
            self,
            chunk_token_size: int = 512,
            llm_model_max_token_size: int = 32768,
            chunk_overlap_token_size: int = 256,
            embedding_dim: int = 1536

    ):
        self.chunk_token_size = chunk_token_size
        self.llm_model_max_token_size = llm_model_max_token_size
        self.chunk_overlap_token_size = chunk_overlap_token_size
        self.embedding_dim = embedding_dim
        self.rag = asyncio.run(self.__initialize_rag())

    async def load_documents(self, documents: list[str], links: list[str]):
        await self.rag.ainsert(input=documents, file_paths=links)

    async def __initialize_rag(self):
        print("init LightRAG")

        light_rag = LightRAG(
            working_dir=WORKING_DIR,
            llm_model_func=ollama_model_complete,
            llm_model_max_token_size=self.llm_model_max_token_size,
            #llm_model_func=ollama_model_complete(prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs)
            #embedding_func=ollama_embed(),
            embedding_func=OllamaEmbedWrapper(),
            chunk_token_size=self.chunk_token_size,
            chunk_overlap_token_size=self.chunk_overlap_token_size,
            kv_storage="JsonKVStorage",
            graph_storage="NetworkXStorage",
            vector_storage="NanoVectorDBStorage",
            doc_status_storage="JsonDocStatusStorage",
            embedding_func_max_async=10,
            llm_model_max_async=10,
            max_parallel_insert=10,
            embedding_cache_config={"enabled": True, "similarity_threshold": 0.9, "use_llm_check": True},
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
    response = rag.get_answer(question="Which article of AI ACT states AI literacy?")
    print(response)
