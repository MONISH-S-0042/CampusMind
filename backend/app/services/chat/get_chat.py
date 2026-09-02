from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.services.authentication.auth import verify_token
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User,Chat

router = APIRouter()

@router.get("/open")
def retrive_chat(payload = Depends(verify_token), db:Session = Depends(get_db)):
    user_id=int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    chat = db.query(Chat).filter(Chat.user_id == user_id).first()
    if not chat:
        chat = Chat(
            user_id = user_id,
            title = "New chat",
            created_at = datetime.now(timezone.utc),
            updated_at = datetime.now(timezone.utc),
        )
        db.add(chat)
        try:
            db.commit()
            db.refresh(chat)
        except:
            db.rollback()
            return {
                "message":"Failed to create chat. Try again"
            }
    return {
        "user_id": user_id,
        "chat_id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at
    }