from fastapi import FastAPI
from gr_base import *

args={
        "neo4j_uri": NEO4J_URI, 
        "neo4j_username": NEO4J_USERNAME, 
        "neo4j_password": NEO4J_PASSWORD,
        "neo4j_database": NEO4J_DATABASE,
    }

app = FastAPI()
graphReaderBase = GraphReaderBase(args=args)

@app.get("/gr_base")
def get_question(question:str):
    return graphReaderBase.get_answer(question=question)