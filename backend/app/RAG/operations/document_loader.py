import os
from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.db.database import session
from backend.app.db.models import Document

class DocumentLoader:
    
    def __init__(self, dir_path:str, db:Session):
        self.dir_path = Path(dir_path)
        self.db=db
    
    def load_documents(self):
        all_documents = []
        print("Executing...")
        #Loading pdf files
        pdf_files = list(self.dir_path.glob("**/*.pdf"))
        print(pdf_files)
        for pdf_file in pdf_files:
            print(f"Processing {pdf_file.name} file....")
            if self._is_document_available(pdf_file):
                print("Already added")
                continue
            try:
                loader = PyPDFLoader(pdf_file)
                #Gives list of document where each page is a document
                documents = loader.load()
                
                for doc in documents:
                    doc.metadata['file_type'] = 'pdf'
                    doc.metadata['source_file'] = pdf_file.name
                
                all_documents.extend(documents)
                print(f"Loaded {len(documents)} pages in {pdf_file.name}")
                self._save_to_db(pdf_file,"pdf")
                
            except Exception as e:
                print(f"Error while loading {pdf_file.name} : {e}")
            
        return all_documents
    
    def _is_document_available(self,file_path:Path):
        try:
            file = self.db.query(Document).filter(Document.file_path == str(file_path)).first()
            if not file:
                return False
            return True
        
        except Exception as e:
            print(f"Error while checking the file {file_path.name} in db: {e}")
            return False
        
    def _save_to_db(self, file_path:Path, file_type:str):
        try:
            file = Document(
                    file_name=file_path.name,
                    file_type=file_type,
                    last_updated=datetime.now(timezone.utc),
                    file_path=str(file_path)
            )
            
            self.db.add(file)
            self.db.commit()
            print(f"Successfully added {file_path.name} to database")
        except Exception as e:
            print(f"Error while adding log of {file_path.name} to database :{e}")
            self.db.rollback()
        
db=session()
doc_loader = DocumentLoader("backend/app/RAG/data",db)
documents = doc_loader.load_documents()
db.close()
