import pymongo, json
from minio import Minio
from urllib.parse import quote_plus
from bson.objectid import ObjectId

class ObjectUploader:
   def __init__(self):
      self.bucket_rate = "rate"
      self.minioClient = Minio(
            endpoint="localhost:9900",
            secure=False,
            access_key="minioadmin",
            secret_key="minioadmin"
      )
      
      uri = "mongodb://%s:%s@%s:%s" % (
            quote_plus("user"),
            quote_plus("Passw0rd!"),
            "localhost",
            "27017"
         )
      self.mongoClient = pymongo.MongoClient(uri)
      
   def downloader_minio(self):
      object_list = []
      
      if self.minioClient.bucket_exists(self.bucket_rate):
          for oggetto in self.minioClient.list_objects(self.bucket_rate):
            oggetto_name = oggetto.object_name
            id_oggetto = oggetto_name.split('_')[-1].replace('.json','')
            risposta = self.minioClient.get_object(bucket_name=self.bucket_rate, object_name=oggetto_name)
            content = risposta.data.decode("utf-8")

            json_content = json.loads(content)
            
            json_content["_id"] = ObjectId(oid=id_oggetto[:24])
            object_list.append(json_content)
            
            mongodb = self.mongoClient['admin']
            if 'rates' not in mongodb.list_collection_names():
               mongodb.create_collection(name="rates")

            mongodb['rates'].insert_one(json_content)


objectloader = ObjectUploader()
objectloader.downloader_minio()