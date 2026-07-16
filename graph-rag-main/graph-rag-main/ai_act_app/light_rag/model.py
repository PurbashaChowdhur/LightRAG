from typing_extensions import Annotated
from fastapi import Query
from pydantic import BaseModel

class Config(BaseModel):
    chunk_token_size:Annotated[int, Query(gt=0)] = 512
    llm_model_max_token_size:Annotated[int, Query(gt=0)] = 32768
    chunk_overlap_token_size:Annotated[int, Query(gt=0)] = 256

class Project(BaseModel):
    sector:str
    purpose:str
    user:str
    training_data:str
    sources:str
    output:str
    other_info:str | None

#Nuovo oggetto RatedResponse; contiene la domanda, la risposta del chatbot e il feedback (1 a 5)
class RatedResponse(BaseModel):
    question:str
    response:str
    feedback:int
    expected_answer:str | None