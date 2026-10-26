import os
from typing import Any, List
import numpy as np
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from app.RAG.operations.embedding_manager import get_embedding_model_dimension

load_dotenv()

class VectorStore:
    """Manages the document embeddings in chromaDB vector Store"""
    def __init__(self, collection_name:str="regulation_documents", vector_size:int = 768):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = None
        self._initialize_store()
        
    def _initialize_store(self):
        try:
            self.client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY")
            )
            if not self.client.collection_exists(self.collection_name):
                print("Creating the Qdrant collection...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size = self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
            info = self.client.get_collection(self.collection_name)
            print("Qdrant collection initialized: ",self.collection_name)
            print(f"Existing point count: {info.points_count}")
            
        except Exception as e:
            print(f"Error initializing the vectorDB: {e}")
            raise
        
    def add_documents(self, documents:List[Any], embeddings: np.ndarray, batch_size:int = 100):
        if(len(documents)!=len(embeddings)):
            raise ValueError("Number of document chunks and embedding are different")
        print(f"Adding {len(documents)} documents to VectorDB...")
        
        points = []
        
        for doc,embedding in zip(documents, embeddings):
            metadata = dict(doc.metadata)
            payload = {
                "page_content":doc.page_content,
                "metadata":metadata
            }
            points.append(
                models.PointStruct(
                    id = str(uuid.uuid4()),
                    vector = embedding.tolist(),
                    payload = payload
                )
            )
            
        try:
            for i in range(0,len(points),batch_size):
                batch = points[i:i+batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                    wait=True
                )
                print(f"Batch {i//100 +1} Processed")
            
            info = self.client.get_collection(self.collection_name)
            print(f"Existing point count: {info.points_count}")
            
        except Exception as e:
            print(f"Error adding files to vectorDB: {e}")
            raise

vector_store = VectorStore(vector_size=get_embedding_model_dimension())

def get_vector_store():
    return vector_store