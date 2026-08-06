
from typing import Any, Dict, List

from app.RAG.operations.embedding_manager import EmbeddingManager
from app.RAG.operations.vectore_store import VectorStore


class RAGRetriver:
    
    def __init__(self, vector_store:VectorStore, embedding_manager: EmbeddingManager):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        print(self.vector_store.collection.metadata)
    
    def retrive(self,query:str, top_k = 5, score_threshold:float = 0.2)->List[Dict[str,Any]]:
        query_embeddings = self.embedding_manager.generate_embeddings([query])[0]
        
        try:
            results = self.vector_store.collection.query(
                query_embeddings=[query_embeddings.tolist()],
                n_results=top_k
            )
            
            retrived_docs = []
            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0] #Because chromaDB supports multiple queries simultaneouly it return nested lists(we need for query 0)
                metadatas = results['metadatas'][0]
                ids = results['ids'][0]
                distances = results['distances'][0]
                
                for i,(doc_id, doc, metadata, distance ) in enumerate(zip(ids,documents,metadatas,distances)):
                    similarity_score = 1-distance
                    if similarity_score >= score_threshold:
                        retrived_docs.append({
                            'id':doc_id,
                            'content':doc,
                            'metadata':metadata,
                            'similarity_score':similarity_score,
                            'distance':distance,
                            'rank':i+1
                        })
                print(f"Retrived {len(retrived_docs)} documents")
            else:
                print("No documents Found")
            return retrived_docs
        except Exception as e:
            print(f"Error retriving document : {e}")
            return []
        