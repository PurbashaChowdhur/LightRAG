# Per acccedere al bucket rag scrivere questo sul terminale --> minio server .data
# minio server --address "0.0.0.0:9000" .data

import json, re, io, os, hashlib
from minio import Minio
from model import RatedResponse

class ObjectStorage:
    def __init__(self):
        self.pattern = re.compile(r'\w+/\w+_(\d+).json')
        self.client = Minio(
            endpoint=os.environ.get("OBJECT_STORAGE_ENDPOINT"),
            secure=False,
            access_key="minioadmin",
            secret_key="minioadmin"
        )

        if not self.client.bucket_exists("rag"):
            self.client.make_bucket("rag")
            

    def __get_reference_number(self, object_name: str):
        match = self.pattern.match(object_name)
        if match is not None and len(match.groups()) > 0:
            return match.group(1)

    def get_content_and_source(self, object_name: str, object_content: dict):
        if 'article' in object_name:
            full_content = f"""
                Article: {object_content["id"]}
                Title: {object_content["title"]}
                Content: {object_content["content"]}
            """
            link = f"https://artificialintelligenceact.eu/article/{self.__get_reference_number(object_name)}/"
            return full_content, link
        else:
            full_content = f"""
                Recital: {object_content["id"]}
                Content: {object_content["content"]}
            """
            link = f"https://artificialintelligenceact.eu/recital/{self.__get_reference_number(object_name)}/"
            return full_content, link

    def get_articles(self):
        articles = []
        sources = []

        for object in self.client.list_objects(bucket_name="rag", recursive=True):
            oggetto = object.object_name
            # print(oggetto)

            try:
                response = self.client.get_object("rag", oggetto)
                content = response.data.decode("utf-8")
                article = json.loads(content)
                content, source = self.get_content_and_source(object_name=oggetto, object_content=article)

                articles.append(content)  # article["content"])
                sources.append(source)
            finally:
                response.close()
                response.release_conn()
        return articles, sources

    def save_feedback(self, rate: RatedResponse):
        if not self.client.bucket_exists("rate"):
            self.client.make_bucket("rate")
        json_data = rate.model_dump_json()
        encoded_data = json_data.encode("utf-8")
        object_name = f"rated_response_{hashlib.sha512(encoded_data).hexdigest()}.json"
        self.client.put_object(bucket_name="rate",
                               object_name=object_name,
                               data=io.BytesIO(encoded_data),
                               content_type="json",
                               length=len(encoded_data))


# object_storage = ObjectStorage()
# object_storage.get_articles()
