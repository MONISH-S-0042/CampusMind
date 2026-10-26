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
            results = self.vector_store.client.query_points(
                collection_name=self.vector_store.collection_name,
                query=query_embeddings.tolist(),
                limit = top_k_vectordb,
                with_payload=True,
                with_vectors=False
            )
            points = results.points
            retrived_docs = []
            if points:
                documents = [point.payload.get("page_content","") for point in points]
                metadatas = [point.payload.get("metadata","") for point in points]
                ids = [point.id for point in points]
                vector_scores = [point.score for point in points]
                #Reranking
                pairs = [[query,doc] for doc in documents]
                scores = self.rerankModel.predict(pairs)
                scored_docs = []
                
                for (doc_id, doc, metadata, vector_score, score ) in zip(ids,documents,metadatas,vector_scores,scores):
                    scored_docs.append({
                            'id':doc_id,
                            'content':doc,
                            'metadata':metadata,
                            'similarity_score':float(score), #From the reranker
                            'vector_score':float(vector_score)
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
        