from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__="User"
    id=Column(Integer,autoincrement=True,primary_key=True)
    name=Column(String,nullable=False)
    password=Column(String,nullable=False)