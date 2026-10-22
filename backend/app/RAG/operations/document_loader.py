import tempfile
from typing import List

from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Document
from app.services.utilities.time import IST
from app.RAG.operations.r2_client import r2_client, BUCKET_NAME

class DocumentLoader:
    
    def __init__(self, db:Session):
        self.db=db
    
    def _get_all_file_keys(self):
        file_keys = []
        paginator = r2_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket = BUCKET_NAME):
            for obj in page.get("Contents",[]):
                file_keys.append(obj["Key"])
        return file_keys
        
    def load_documents(self):
        all_documents = []
        print("Executing...")
        file_keys = self._get_all_file_keys()
        
        for file_key in file_keys:
            key_path = Path(file_key)
            extension = key_path.suffix.lower()
            if extension not in {".pdf",".txt"}:
                continue
            file_type = extension.lstrip(".")
            
            print(f"Processing {file_key}...")
            if(self._is_document_available(file_key)):
                print("Already added")
                continue
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    local_path = Path(temp_dir) / key_path.name
                    r2_client.download_file(
                        BUCKET_NAME,
                        file_key,
                        str(local_path)
                    )
                    if file_type == "pdf":
                        loader = PyMuPDFLoader(str(local_path))
                    else:
                        loader = TextLoader(str(local_path))
                    
                    documents = loader.load()
                    for doc in documents:
                        doc.metadata["file_type"] = file_type
                        doc.metadata["source_file"] = key_path.name
                        doc.metadata["source_key"] = file_key
                        
                    all_documents.extend(documents)

                print(f"Loaded {len(documents)} document(s) from {file_key}")
            except Exception as e:
                print(f"Error while loading {file_key}: {e}")
                
        return all_documents
    
    def _is_document_available(self,file_key:str):
        try:
            file = self.db.query(Document).filter(Document.file_path == file_key).first()
            if not file:
                return False
            return True
        
        except Exception as e:
            print(f"Error while checking the file {file_key} in db: {e}")
            return False
        
        
        
        
class DocumentSplitter:
    
    def __init__(self,chunk_size:int, chunk_overlap:int):
        self.chunk_size=chunk_size
        self.chunk_overlap=chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n","\n"," ",""]
        )
    
    def split_documents(self,documents:List[Document]):
        return self.text_splitter.split_documents(documents)

