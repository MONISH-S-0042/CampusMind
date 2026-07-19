from fastapi import Depends, FastAPI
from app.db.database import engine, get_db
from app.db.models import Base, User
from sqlalchemy.orm import Session
from app.services.authentication import auth
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
