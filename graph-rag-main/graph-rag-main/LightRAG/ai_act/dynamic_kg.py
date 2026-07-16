# --- new_hybrid_runner.py ---
import os, json, asyncio, re
from pathlib import Path

# 1) Your LightRAG setup (unchanged)
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete
from lightrag.kg.shared_storage import initialize_pipeline_status

# 2) Your iText2KG setup
from itext2kg.documents_distiller import DocumentsDistiller
from itext2kg.models import Facts
from itext2kg import iText2KG_Star
from itext2kg.graph_integration import Neo4jStorage

# ---------- CONFIG ----------
CACHED_ARTICLE_PATH = "./cached_docs/article_{}.json"   # 1..113
CACHED_RECITAL_PATH = "./cached_docs/recital_{}.json"   # 1..180
OBSERVATION_DATE = "Jul 31 2025"

# secrets via env (rotate your leaked keys!)
MISTRAL_API_KEY = os.getenv("fSPwhqsQrbLAClU08MpZ8Op3fk8c4wsL")
OPENAI_API_KEY  = os.getenv("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")

#NEO4J_URI  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
#NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
#NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

# LightRAG working dir
WORKING_DIR = "./rag"
os.makedirs(WORKING_DIR, exist_ok=True)

# ---------- UTILS ----------
def load_cached_ai_act():
    docs, sources = [], []
    # articles
    for i in range(1, 114):
        p = CACHED_ARTICLE_PATH.format(i)
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        docs.append(j["content"])
        sources.append(p)
    # recitals
    for i in range(1, 181):
        p = CACHED_RECITAL_PATH.format(i)
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        docs.append(j["content"])
        sources.append(p)
    return docs, sources

# ---------- RAG (unchanged core) ----------
async def init_lightrag():
    lr = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=gpt_4o_mini_complete,
        llm_model_max_token_size=32768,
        embedding_func=openai_embed,
        chunk_token_size=512,
        chunk_overlap_token_size=256,
        kv_storage="JsonKVStorage",
        graph_storage="NetworkXStorage",
        vector_storage="NanoVectorDBStorage",
        doc_status_storage="JsonDocStatusStorage",
        embedding_func_max_async=10,
        llm_model_max_async=10,
        max_parallel_insert=10,
        embedding_cache_config={"enabled": True, "similarity_threshold": 0.9, "use_llm_check": True},
        addon_params={}  # you can pass your ontology entity types here if needed
    )
    await lr.initialize_storages()
    await initialize_pipeline_status()
    return lr

# ---------- iText2KG ----------
from langchain_mistralai import ChatMistralAI
from langchain_openai import OpenAIEmbeddings

IE_QUERY = """# DIRECTIVES :
- Act like an experienced information extractor.
- Extract: definitions, roles, obligations, prohibitions, risk classes, transparency duties, GPAI rules, governance, conformity assessment, timelines, penalties, derogations, market surveillance, innovation measures.
- Preserve article/recital references when visible.
"""

mistral_llm = ChatMistralAI(api_key=MISTRAL_API_KEY, model="mistral-large-latest", temperature=0, max_retries=2)
openai_emb  = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-large")
distiller   = DocumentsDistiller(llm_model=mistral_llm)

async def distill_chunks(texts):
    tasks = [
        distiller.distill(documents=[t], IE_query=IE_QUERY, output_data_structure=Facts)
        for t in texts
    ]
    return await asyncio.gather(*tasks)

async def build_itext2kg(facts_list):
    star = iText2KG_Star(llm_model=mistral_llm, embeddings_model=openai_emb)
    kg = None
    for idx, facts in enumerate(facts_list):
        kg = await star.build_graph(
            sections=facts.facts,
            # observation_date=OBSERVATION_DATE,
            ent_threshold=0.8,
            rel_threshold=0.7,
            existing_knowledge_graph=(kg.model_copy() if kg else None)
        )
        #if (idx + 1) % 20 == 0:
        #    print(f"[KG] Integrated {idx+1}/{len(facts_list)} segments …")
    # Neo4jStorage(uri=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS).visualize_graph(knowledge_graph=kg)
    # return kg

# ---------- MAIN ----------
async def main():
    docs, sources = load_cached_ai_act()

    # A) index in LightRAG (your current behavior)
    lightrag = await init_lightrag()
    await lightrag.ainsert(input=docs, file_paths=sources)

    # B) distill and build KG from the same docs
    facts_list = await distill_chunks(docs)
    await build_itext2kg(facts_list)

    # Example query to LightRAG
    answer = lightrag.query("What obligations do providers of high-risk AI have about post-market monitoring?",
                            param=QueryParam(mode="hybrid"))
    print("RAG answer:\n", answer)

if __name__ == "__main__":
    asyncio.run(main())
