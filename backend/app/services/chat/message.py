from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from app.db.models import Message, Chat, User
from app.services.authentication.auth import verify_token
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.RAG.operations.retrival_pipeline import get_retrival_pipeleine

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
    try:
        db.commit()
        db.refresh(message)
    except:
        db.rollback()
        return {
            "message":"Failed to save message. Try again"
        }
    retriver = get_retrival_pipeleine()
    res = {
        "message_id":message.id,
        "message":query,
        "chat_id":message.chat_id
    }
    response = retriver.process_query(query, top_k=10)
    if response and response.get("answer") and len(response.get("answer"))>0:
        message = Message(
            chat_id = chat_id,
            role = 'AI',
            content = response.get("answer")[0].get("text"),
            created_at = datetime.now(timezone.utc)
        )
        db.add(message)
        try:
            db.commit()
            db.refresh(message)
        except:
            db.rollback()
            return {
                "message":"Failed to save the response. Try again"
            }
        res["response"] = response.get("answer")[0].get("text")
    return res