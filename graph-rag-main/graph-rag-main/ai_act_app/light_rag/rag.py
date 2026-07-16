import sys
import os
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from typing import Literal
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete
from lightrag.kg.shared_storage import initialize_pipeline_status
from model import Config, Project
from minio_executor import ObjectStorage

CACHED_ARTICLE_PATH = "./cached_docs/article_{}.json"
CACHED_RECITAL_PATH = "./cached_docs/recital_{}.json"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.join(ROOT_DIR, "rag")

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)
print(f"WorkingDir: {WORKING_DIR}")

os.environ[
    "OPENAI_API_KEY"] = "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"


class RAG:
    def __init__(self):
        print("RAG.__init__")
        self.objectStorage = ObjectStorage()
        self.rag = None

    async def load_documents(self, documents: list[str], links: list[str]):
        await self.rag.ainsert(input=documents, file_paths=links)

    async def initialize_rag(self, config: Config):
        print("RAG.initialize_rag")

        light_rag = LightRAG(
            working_dir=WORKING_DIR,
            llm_model_func=gpt_4o_mini_complete,
            llm_model_max_token_size=config.llm_model_max_token_size,
            embedding_func=openai_embed,
            chunk_token_size=config.chunk_token_size,
            chunk_overlap_token_size=config.chunk_overlap_token_size,
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
        self.rag = light_rag

    async def get_answer(self, question: str,
                         mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"] = "hybrid"):
        print(f"Retrieving answer for question: {question}")

        print(self.rag)
        answer = await self.rag.aquery(
            question,
            param=QueryParam(mode=mode)
        )

        return answer

    async def load_docs(self):
        documents, sources = self.objectStorage.get_articles()

        await self.load_documents(documents=documents, links=sources)
        return {
            "num_documents": len(documents)
        }

    def load_questions(self, category):
        file_path = 'risk_assessment_questions.json'

        with open(file_path, 'r') as file:
            data = json.load(file)
        questions = [item for item in data if item['category'] == category]
        return questions

    async def ai_act_assessment(self, project: Project, category: str):
        description = f"""
            {project.sector}
            {project.purpose}
            {project.user}
            {project.training_data}
            {project.sources}
            {project.output}
            {project.other_info}
        """

        question = f"""You are a compliance expert, acting as an advisor in assessing AI systems.
            Your role is to help users to reply to some questions in order to assess the risk level of an AI system according the EU AI Act. 
            You need to reply to the questions given a description of the AI system. 
            Reply to each question with "Yes", "No" or "Don't know", the answer will depend on the information contained in the description given. 
            You need to answer "Don't know" if there are not enough information in the description in order to reply to the question.
            Do not guess the answer to any questions, reply only based on the information contained in the description.
            The questions will be given as a list with three fields in a json format as follows:

            "category":"prohibited"
            "id":"2.4"
            "question":"Does your AI system assesses or predicts the risk of a person committing a criminal offence, based solely on the profiling of a person or on assessing their personality traits and characteristic?"    

            You need to answer to the question contained in the field "question". 
            Some questions will have sub questions nested inside. The sub questions have a flag indicating exception or follow-ups. Below are reported two examples:

            "category":"prohibited"
            "id":"2.4"
            "question":"Does your AI system assesses or predicts the risk of a person committing a criminal offence, based solely on the profiling of a person or on assessing their personality traits and characteristic?"
            "sub_questions":
            "id":"2.4.1"
            "flag": "exception",
            "question":"Is your AI system used to support the human assessment of the involvement of a person in a criminal activity, which is already based on objective and verifiable facts directly linked to a criminal activity?"
            "widget": "Article 5.1(d): The placing on the market, the putting into service for this specific purpose, or the use of an AI system for making risk assessments of natural persons in order to assess or predict the risk of a natural person committing a criminal offence, based solely on the profiling of a natural person or on assessing their personality traits and characteristics; this prohibition shall not apply to AI systems used to support the human assessment of the involvement of a person in a criminal activity, which is already based on objective and verifiable facts directly linked to a criminal activity."
            
            "category": "prohibited",
            "id": "2.3",
            "question": "Does your AI system perform social scoring for the evaluation or classification of individuals or groups based on their social behaviour or known, inferred or predicted personal or personality characteristics?",
            "widget": "Article 5.1(c): the placing on the market, the putting into service or the use of AI systems for the evaluation or classification of natural persons or groups of persons over a certain period of time based on their social behaviour or known, inferred or predicted personal or personality characteristics, with the social score leading to either or both of the following: \n(i) detrimental or unfavourable treatment of certain natural persons or groups of persons in social contexts that are unrelated to the contexts in which the data was originally generated or collected.\n(ii) detrimental or unfavourable treatment of certain natural persons or groups of persons that is unjustified or disproportionate to their social behaviour or its gravity.",
            "sub_questions": 
            "id": "2.3.1",
            "flag": "follow-up",
            "question": "Does the social score lead to detrimental or unfavourable treatment of certain natural individuals or whole groups thereof in social contexts that are unrelated to the contexts in which the data was originally generated or collected?",
            "widget": "Article 5.1(c): the placing on the market, the putting into service or the use of AI systems for the evaluation or classification of natural persons or groups of persons over a certain period of time based on their social behaviour or known, inferred or predicted personal or personality characteristics, with the social score leading to either or both of the following: \n(i) detrimental or unfavourable treatment of certain natural persons or groups of persons in social contexts that are unrelated to the contexts in which the data was originally generated or collected.\n(ii) detrimental or unfavourable treatment of certain natural persons or groups of persons that is unjustified or disproportionate to their social behaviour or its gravity."

            
            Reply to the question contained in the sub_question only if the answer of the question in which the sub_question is nested is Yes, otherwise the answer to the sub question will be "N/A". The answer of the sub question should be "N/A" only in the case the answer of the parent question is "No" otherwise needs to be either "Yes", "No" or "I don't Know" based on the description.
            Format your output as json string using the same json format as the input adding your answer as the field "answer" and omitting the field "widget" in each question or sub_questions. 
            The string needs to be in a correct json format so it can be converted in dict format. Do not output anything else.
            Your language should be polite, impersonal, corporate acceptable, and avoid using personal pronouns (I, we, ...).

            Let's start:
            The description is the following:
            {description}
            The questions which you need to reply are the following:
            {self.load_questions(category=category)}
            """
        answers = await self.rag.aquery(query=question)
        return answers


# r = RAG()
# config = Config()
# asyncio.run(r.initialize_rag(config=config))
# asyncio.run(r.load_docs())

if __name__ == '__main__':
    import asyncio

    r = RAG()
    config = Config()
    asyncio.run(r.initialize_rag(config=config))
