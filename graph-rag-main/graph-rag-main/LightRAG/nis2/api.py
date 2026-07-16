from fastapi import FastAPI
from rag import RAG

app = FastAPI()
rag = RAG()


@app.get("/response")
def get_response(question: str):
    return {"response": rag.get_answer(question=question)}
