from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__="User"
    id=Column(Integer,primary_key=True, index=True)
    username=Column(String,nullable=False, unique= True)
    hashed_password=Column(String,nullable=False)
    chats = relationship("Chat", back_populates="user")
    remainders = relationship("Remainder", back_populates="user")
    
class Chat(Base):
    __tablename__="Chat"
    id=Column(Integer,primary_key=True, index=True)
    user_id=Column(Integer, ForeignKey("User.id"),nullable=False)
    title=Column(String)
    created_at=Column(DateTime,nullable=False)
    updated_at=Column(DateTime,nullable=False)
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")
    
class Message(Base):
    __tablename__="Message"
    id=Column(Integer,primary_key=True,index=True)
    chat_id=Column(Integer, ForeignKey("Chat.id"),nullable=False)
    role=Column(String,nullable=False) #User or AI
    content=Column(String)
    created_at=Column(DateTime)
    chat = relationship("Chat", back_populates="messages")

class Document(Base):
    __tablename__="Document"
    id=Column(Integer, primary_key=True,index=True)
    file_name=Column(String,nullable=False)
    file_type=Column(String,nullable=False)
    last_updated=Column(DateTime, nullable=False)
    file_path=Column(String,nullable=False,unique=True)
    
    
class Remainder(Base):
    __tablename__="Remainder"
    id=Column(Integer,primary_key=True,index=True)
    remainder_time=Column(DateTime(timezone=True))
    course_name=Column(String)
    is_active=Column(Boolean)
    event_type=Column(String)
    extra_info=Column(String)
    user_id = Column(Integer,ForeignKey("User.id"),nullable=False)
    user = relationship("User", back_populates="remainders")