from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from app.RAG.operations.document_loader import DocumentLoader, DocumentSplitter
from app.RAG.operations.embedding_manager import get_embedding_manager
from app.RAG.operations.vectore_store import get_vector_store
from app.db.models import Document
from app.services.utilities.time import IST

class DataIngestion:
    
    def __init__(self,db:Session):
        self.db = db
        self.document_loader = DocumentLoader(db)
        self.document_splitter = DocumentSplitter(600,200)
        self.embedding_manager = get_embedding_manager()
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
        processed_files = {}
        for doc in self.all_documents:
            key = doc.metadata["source_key"]
            file_type = doc.metadata["file_type"]
            processed_files[key] = file_type
        for file_key, file_type in processed_files.items():
            self._save_to_db(file_key, file_type)
        
        print(f"Data Ingestion completed")
        
    def _save_to_db(self, file_key:str, file_type:str):
        try:
            file = Document(
                    file_name=Path(file_key).name,
                    file_type=file_type,
                    last_updated=datetime.now(IST),
                    file_path=file_key
            )
            
            self.db.add(file)
            self.db.commit()
            print(f"Successfully added {file_key} to database")
        except Exception as e:
            print(f"Error while adding log of {file_key} to database :{e}")
            self.db.rollback()

