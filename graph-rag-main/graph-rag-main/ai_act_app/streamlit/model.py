from pydantic import BaseModel

#Nuovo oggetto RatedResponse; contiene la domanda, la risposta del chatbot e il feedback (1 a 5)
class RatedResponse(BaseModel):
    question:str
    response:str
    feedback:int
    expected_answer:str | None