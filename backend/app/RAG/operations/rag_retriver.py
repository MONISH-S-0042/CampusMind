from sentence_transformers import CrossEncoder
from typing import Any, Dict, List

from app.RAG.operations.embedding_manager import EmbeddingManager
from app.RAG.operations.vectore_store import VectorStore


class RAGRetriver:
    
    def __init__(self, vector_store:VectorStore, embedding_manager: EmbeddingManager, rerankModel:CrossEncoder):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.rerankModel = rerankModel
    
    def retrive(self,query:str, top_k = 5)->List[Dict[str,Any]]:
        query_embeddings = self.embedding_manager.generate_embeddings([query])[0]
        
        try:
            top_k_vectordb = top_k*6
            results = self.vector_store.collection.query(
                query_embeddings=[query_embeddings.tolist()],
                n_results=top_k_vectordb
            )
            
            retrived_docs = []
            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0] #Because chromaDB supports multiple queries simultaneouly it return nested lists(we need for query 0)
                metadatas = results['metadatas'][0]
                ids = results['ids'][0]
                distances = results['distances'][0]
                #Reranking
                pairs = [[query,doc] for doc in documents]
                scores = self.rerankModel.predict(pairs)
                scored_docs = []
                
                for (doc_id, doc, metadata, distance, score ) in zip(ids,documents,metadatas,distances,scores):
                    scored_docs.append({
                            'id':doc_id,
                            'content':doc,
                            'metadata':metadata,
                            'similarity_score':float(score), #From the reranker
                            'distance':distance
                    })
                scored_docs.sort(key=lambda x:x.get('similarity_score'), reverse = True)
                
                for i,item in enumerate(scored_docs):
                    item['rank'] = i+1
                    retrived_docs.append(item)
                    
                    if len(retrived_docs)>=top_k:
                        break
                
                print(f"Retrived and reranked {len(retrived_docs)} documents")
            else:
                print("No documents Found")
            return retrived_docs
        except Exception as e:
            print(f"Error retriving document : {e}")
            return []
        