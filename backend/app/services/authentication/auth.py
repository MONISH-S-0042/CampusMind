from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException,Header
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from pwdlib import PasswordHash
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "campus_mind_secret"
ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter()

#TO HASH THE PLAIN PASSWORD
def hash_password(password: str):
    return password_hash.hash(password=password)

#TO VERIFY PLAIN PASSWORD WITH HASHED PASSWORD
def verify_password(plain_password: str, hashed_password:str):
    return password_hash.verify(plain_password, hashed_password)
    
#TO GENERATE JWT TOKEN
def create_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=120)
    to_encode.update({
        "exp":expire
    })
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

#TO VERIFY TOKEN
def verify_token(token:str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        print(e)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

@router.post("/register")
def register(username:str, password:str, db:Session= Depends(get_db)):
    try:
        existing_user=db.query(User).filter(User.username==username).first()
    except:
        raise HTTPException(
            status_code=500,
            detail="Server side error"
        )
    if existing_user:
        raise HTTPException(status_code=401, detail="Username not available")
    user = User(username=username, hashed_password=hash_password(password))
    db.add(user)
    try:
        db.commit()
        return {"message: successfuly registered"}
    except:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Server side error"
        )
    
@router.post("/login")
def login(username:str, password:str, db:Session= Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
    except:
        raise HTTPException(
            status_code=500,
            detail="Server side error"
        )
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
    )
    hashed_password = user.hashed_password
    if not verify_password(plain_password=password, hashed_password=hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
    )
    return {"access_token": create_token({"sub": str(user.id)}), "token_type": "bearer"}

    
@router.get("/content")
def home(payload = Depends(verify_token), db:Session = Depends(get_db)):
    try:
        user_id=int(payload["sub"])
        user = db.query(User).filter(User.id == user_id).first()
    except:
        raise HTTPException(
            status_code=500,
            detail="Server side error"
        )
    if not user:
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return {
        "message":"Secure Data accessed",
        "user":user
    }