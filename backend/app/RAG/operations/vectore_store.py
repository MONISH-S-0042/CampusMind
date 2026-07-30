import os
from typing import Any, List
import numpy as np
import chromadb
import uuid

class VectorStore:
    """Manages the document embeddings in chromaDB vector Store"""
    def __init__(self, collection_name:str="regulation_documents", persist_directory:str="app/RAG/data/vector_store"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self._initialize_store()
        
    def _initialize_store(self):
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            self.collection = self.client.get_or_create_collection(
                name = self.collection_name,
                metadata={"description":"stores the regulation files"}   
            )
            print(f"Vector store initialized. Collection {self.collection_name}")
            print(f"Existing document count in {self.collection_name}: {self.collection.count()}")
            
        except Exception as e:
            print(f"Error initializing the vectorDB: {e}")
            raise
        
    def add_documents(self, documents:List[Any], embeddings: np.ndarray, batch_size:int = 100):
        if(len(documents)!=len(embeddings)):
            raise ValueError("Number of document chunks and embedding are different")
        print(f"Adding {len(documents)} documents to VectorDB...")
        
        ids = []
        metadatas = []
        embeddings_list = []
        document_texts = []
        
        for i,(doc,embedding) in enumerate(zip(documents, embeddings)):
            doc_id = f"doc_{uuid.uuid4().hex[:8]}_{i}"
            ids.append(doc_id)
            metadata = dict(doc.metadata)
            metadata['document_index']=i
            metadata['content_length']=len(doc.page_content)
            metadatas.append(metadata)
            
            document_texts.append(doc.page_content)
            embeddings_list.append(embedding.tolist())
            
        try:
            batch_size = 100
            for i in range(0,len(embeddings),batch_size):
                end = i+batch_size
                self.collection.add(
                    ids=ids[i:end],
                    metadatas=metadatas[i:end],
                    embeddings=embeddings_list[i:end],
                    documents=document_texts[i:end]
                )
                print(f"Batch {i//100 +1} Processed")
            print(f"Total documents in collection: {self.collection.count()}")
            
        except Exception as e:
            print(f"Error adding files to vectorDB: {e}")
            raise

vector_store = VectorStore()

def get_vector_store():
    return vector_store