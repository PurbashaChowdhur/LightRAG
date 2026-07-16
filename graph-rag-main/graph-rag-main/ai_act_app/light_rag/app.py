import json
from fastapi import FastAPI
from rag import RAG
from typing import Literal
from model import Config, Project, RatedResponse
from minio_executor import ObjectStorage

app = FastAPI()
rag = RAG()
objectStorage = ObjectStorage()


#nest_asyncio.apply()

# Domande di prova: dammi la definizione di AI ad alto rischio; dammi la definizione di provider; dammi una definizione di sistema ad alto rischio

@app.get("/lightrag/answer")
async def get_question(question:str, mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = "hybrid"):
    response = await rag.get_answer(question=question, mode=mode)
    return {"response":response}

@app.post("/lightrag/configuration")
async def parameters_config(config:Config):
    return await rag.initialize_rag(config=config)

@app.post("/lightrag/load")
async def loader():
    return await rag.load_docs()

@app.post("/lightrag/ai_act/assessment")
async def parameters_assessment(project:Project, category: Literal["exclusion","prohibited","safety_component","high_risk","exception","general_purpose","systemic_risk"]):
    response = await rag.ai_act_assessment(project=project, category=category)
    response = response.replace("```json", "").replace("```", "")

    return json.loads(response)

#Post che prende il parametro ratedResponse
#Creare un bucket per salvare ogni rates

@app.post("/lightrag/ratedResponse")
def ratedResponse(rate:RatedResponse):
    #print(rate.question,rate.response,rate.feedback)
    objectStorage.save_feedback(rate=rate)