from fastapi import Depends, FastAPI
from app.db.database import engine, get_db
from app.db.models import Base, User
from sqlalchemy.orm import Session
from app.services.authentication import auth
from app.services.chat import get_chat
from app.services.chat import message
from app.RAG.operations.data_ingestion import DataIngestion
from app.RAG.operations.vectore_store import get_vector_store
from app.RAG.operations.retrival_pipeline import get_retrival_pipeleine
app=FastAPI()
Base.metadata.create_all(bind=engine)
app.include_router(auth.router, prefix="/api/auth", tags=["jwt"])
app.include_router(get_chat.router, prefix="/api/chat", tags=["jwt"])
app.include_router(message.router, prefix="/api/chat", tags=["jwt"])

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
    data_ingester = DataIngestion(db)
    data_ingester.ingest_data()
    store = get_vector_store()
    return {"count":store.collection.count()}

@app.get("/query/{val}")
def get_response(val:str):
    retriver = get_retrival_pipeleine()
    response = retriver.process_query(query=val, top_k=10)
    return response