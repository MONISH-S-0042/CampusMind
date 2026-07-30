from sqlalchemy.orm import Session

from app.RAG.operations.document_loader import DocumentLoader, DocumentSplitter
from app.RAG.operations.embedding_manager import EmbeddingManager
from app.RAG.operations.vectore_store import get_vector_store

class DataIngestion:
    
    def __init__(self,db:Session, dir_path:str="app/RAG/data", embedding_model:str = "all-MiniLM-L6-v2"):
        self.db = db
        self.dir_path=dir_path
        self.embedding_model=embedding_model
        self.document_loader = DocumentLoader(dir_path, db)
        self.document_splitter = DocumentSplitter(600,200)
        self.embedding_manager = EmbeddingManager(model_name=embedding_model)
        self.vector_store = get_vector_store()
    
    def ingest_data(self):
        self._load_documents()
        
    def _load_documents(self):
        self.all_documents = self.document_loader.load_documents()
        if(len(self.all_documents)>0):
            self._split_documents()
        else:
            print("No new Documents to Ingest")
    
    def _split_documents(self):
        self.document_chunks = self.document_splitter.split_documents(self.all_documents)
        self._get_embeddings()
        
    def _get_embeddings(self):
        document_texts = [doc.page_content for doc in self.document_chunks]
        self.embeddings = self.embedding_manager.generate_embeddings(document_texts)
        self._add_to_vector_store()
        
    def _add_to_vector_store(self):
        self.vector_store.add_documents(self.document_chunks, self.embeddings)
        print(f"Data Ingestion completed")

