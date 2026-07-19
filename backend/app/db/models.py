from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__="User"
    id=Column(Integer,primary_key=True, index=True)
    username=Column(String,nullable=False, unique= True)
    hashed_password=Column(String,nullable=False)