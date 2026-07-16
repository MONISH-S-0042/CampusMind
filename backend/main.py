from fastapi import Depends, FastAPI
from app.db.database import session, engine
from app.db.models import Base, User
from sqlalchemy.orm import Session

app=FastAPI()
Base.metadata.create_all(bind=engine)
def get_db():
    db=session()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message":"FastAPI working"}

@app.post("/{name}/{password}")
def save(name:str ,password:str, db:Session = Depends(get_db)):
    db.add(User(name=name,password=password))
    db.commit()
    
    return {"Success":"User added"}