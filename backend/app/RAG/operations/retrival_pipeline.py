import os
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder
from app.RAG.operations.embedding_manager import EmbeddingManager, get_embedding_manager
from app.RAG.operations.rag_retriver import RAGRetriver
from app.RAG.operations.vectore_store import VectorStore, get_vector_store
load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
from langchain.chat_models import init_chat_model


class RetrivalPipeline:
    
    def __init__(self, llm, vector_store:VectorStore,embedding_manager:EmbeddingManager, rerankModel:CrossEncoder):
        self.llm = llm
        self.retriver = RAGRetriver(vector_store,embedding_manager, rerankModel)
        
        
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
    
    def _create_prompt(self,query:str, context:str, sources)->str:
        prompt = f"""You are CampusMind, an AI assistant for VIT students.
                Your goal is to answer the user's question based STRICTLY on the provided context.

                === RULES FOR ANSWERING ===
                1. You must extract the answer only from the provided text. Do not use outside knowledge.
                2. You are allowed to use basic deductive reasoning. For example:
                - If the user asks if 'X' is allowed, and the context explicitly prohibits 'X', state that it is prohibited.
                - If the user asks if an item belongs to a specific list, and the context provides the complete list which does not include that item, state clearly that it is not on the list.
                3. If the context completely lacks the information needed to answer the question, do not guess. You must return EXACTLY this phrase and nothing else: "Not Found in Documents".

                === OUTPUT FORMAT ===
                If you find the answer, you MUST place the source file name at the very top of your response, followed by a blank line, and then your answer.

                Context:
                {context}

                Sources:
                {[source.get('source') for source in sources]}

                Question:
                {query}

                Answer:"""
        return prompt
        
    def process_query(self,query:str, top_k:int=5):
        context,sources,confidence = self._retrive(query,top_k)
        prompt = self._create_prompt(query, context, sources)
        try:
            response = self.llm.invoke(prompt)
            
            output = {
                "answer":response.text,
                "source":sources,
                "confidence":confidence
            }
            return output
        
        except Exception as e:
            print(f"Error while processing the request: {e}")
            return ""


    def get_context(self,query:str,top_k:int = 10):
        context,sources,confidence = self._retrive(query,top_k)
        prompt = f"""
                    Context:
                    {context if context else 'No context found'}
                    Sources:
                    {[source.get('source') for source in sources] if sources and len(sources)>0 else 'No sources'}
                    Confidence:
                    {confidence if confidence else 'NIL'}
                    Question asked in current turn:
                    {query}

                    Answer:"""
        return prompt
    
def get_chat_bot(llm_name:str):
    llm = init_chat_model(model=llm_name)
    return llm

vector_store = get_vector_store()
embedding_manager = get_embedding_manager()
rerankModel = CrossEncoder("BAAI/bge-reranker-base", local_files_only=True)
llm = get_chat_bot("google_genai:gemini-3.5-flash-lite")

retrival_pipeline = RetrivalPipeline(llm,vector_store, embedding_manager, rerankModel)

def get_retrival_pipeleine():
    return retrival_pipeline