from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import asc
from app.db.models import Message, Chat
from app.services.authentication.auth import verify_token
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.graph import invoke_graph

router = APIRouter()

@router.post("/{chat_id}/message")
def add_message(chat_id:int, query:str , db:Session = Depends(get_db), payload = Depends(verify_token)):
    user_id=int(payload["sub"])
    chat = db.query(Chat).filter(Chat.id == chat_id , Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )
    message = Message(
        chat_id = chat_id,
        role = 'User',
        content = query,
        created_at = datetime.now(timezone.utc)
    )
    db.add(message)
    chat.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(message)
        db.refresh(chat)
    except:
        db.rollback()
        return {
            "message":"Failed to save message. Try again"
        }
    res = {
        "message_id":message.id,
        "message":query,
        "chat_id":message.chat_id
    }
    config={
        "configurable":{
            "thread_id":f"{user_id}_{chat_id}"
        }
    }
    response = invoke_graph(query,user_id,chat_id)
    if response and  len(response)>0:
        ai_message = Message(
            chat_id = chat_id,
            role = 'AI',
            content = response,
            created_at = datetime.now(timezone.utc)
        )
        db.add(ai_message)
        chat.updated_at = datetime.now(timezone.utc)
        try: 
            db.commit()
            db.refresh(chat)
            db.refresh(ai_message)
        except:
            db.rollback()
            return {
                "message":"Failed to save the response. Try again"
            }
        res["response"] = response
    return res

@router.get("/{chat_id}/messages")
def get_history(chat_id:int, payload =Depends(verify_token), db:Session = Depends(get_db)):
    user_id=int(payload["sub"])
    chat = db.query(Chat).filter(Chat.id == chat_id , Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
    )
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(asc(Message.created_at)).all()
    if not messages:
        return {
            "message":"No messages Found"
        }
    return {
        "chat_id":chat_id,
        "title":chat.title,
        "messages":[
            {
                "id":message.id,
                "role":message.role,
                "content":message.content,
                "created_at":message.created_at
            }
            for message in messages
        ]
    }