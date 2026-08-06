import os
from dotenv import load_dotenv
from app.RAG.operations.embedding_manager import EmbeddingManager, get_embedding_manager
from app.RAG.operations.rag_retriver import RAGRetriver
from app.RAG.operations.vectore_store import VectorStore, get_vector_store
load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
from langchain.chat_models import init_chat_model


class RetrivalPipeline:
    
    def __init__(self, llm, vector_store:VectorStore,embedding_manager:EmbeddingManager):
        self.llm = llm
        self.retriver = RAGRetriver(vector_store,embedding_manager)
        
    def _retrive(self,query:str, top_k:int =5):
        results =  self.retriver.retrive(query,top_k)
        context = "\n\n".join([doc['content'] for doc in results]) if results else ""
        if not results:
            return (None, None,None)
        
        sources = [{
            'source' : doc['metadata'].get('source_file',doc['metadata'].get('source','unknown')),
            'page' : doc['metadata'].get('page','unknown'),
            'score':doc['similarity_score'],
            'preview':doc['content'][:100]+"...."
        } for doc in results]
        
        confidence = max([doc['similarity_score'] for doc in results])
        
        if not context:
            return (None, None,None)

        
        return (context, sources,confidence)
    
    def _create_prompt(self,query:str, context:str)->str:
        prompt = f"""You are CampusMind, an AI assistant for VIT students.

                    Answer ONLY using the provided context. Explain clearly

                    If the answer cannot be found in the context,
                    say that you could not find it in the official
                    documents.

                    Context:
                    {context}

                    Question:
                    {query}

                    Answer:"""
        return prompt
        
    def process_query(self,query:str, top_k:int=5):
        context,sources,confidence = self._retrive(query,top_k)
        prompt = self._create_prompt(query, context)
        try:
            response = self.llm.invoke(prompt)
            
            output = {
                "answer":response.content,
                "source":sources,
                "confidence":confidence
            }
            return output
        
        except Exception as e:
            print(f"Error while processing the request: {e}")
            return ""


def get_chat_bot(llm_name:str):
    llm = init_chat_model(model=llm_name)
    return llm

vector_store = get_vector_store()
embedding_manager = get_embedding_manager()
llm = get_chat_bot("google_genai:gemini-3.5-flash-lite")

retrival_pipeline = RetrivalPipeline(llm,vector_store, embedding_manager)

def get_retrival_pipeleine():
    return retrival_pipeline