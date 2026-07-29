from fastapi import Depends, FastAPI
from app.db.database import engine, get_db
from app.db.models import Base, User
from sqlalchemy.orm import Session
from app.services.authentication import auth
from app.RAG.operations.document_loader import DocumentSplitter,DocumentLoader
from app.RAG.operations.embedding_manager import EmbeddingManager
app=FastAPI()
Base.metadata.create_all(bind=engine)
app.include_router(auth.router, prefix="/api/auth", tags=["jwt"])

@app.get("/")
def home():
    return {"message":"FastAPI working"}

@app.post("/{name}/{password}")
def save(name:str ,password:str, db:Session = Depends(get_db)):
    db.add(User(name=name,password=password))
    db.commit()
    
    return {"Success":"User added"}

@app.get("/chunks")
def chunks(db:Session = Depends(get_db)):
    doc_loader = DocumentLoader("app/RAG/data",db)
    doc_splitter = DocumentSplitter(600,200)

    documents = doc_loader.load_documents()
    print(len(documents))
    document_chunks = doc_splitter.split_documents(documents)
    print(len(document_chunks))
    embedding_manager = EmbeddingManager()
    texts = [doc.page_content for doc in document_chunks]
    embeddings = embedding_manager.generate_embeddings(texts)
    return embeddings.tolist()