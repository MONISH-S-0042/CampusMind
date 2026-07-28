from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__="User"
    id=Column(Integer,primary_key=True, index=True)
    username=Column(String,nullable=False, unique= True)
    hashed_password=Column(String,nullable=False)
    
class Document(Base):
    __tablename__="Document"
    id=Column(Integer, primary_key=True,index=True)
    file_name=Column(String,nullable=False)
    file_type=Column(String,nullable=False)
    last_updated=Column(DateTime, nullable=False)
    file_path=Column(String,nullable=False,unique=True)