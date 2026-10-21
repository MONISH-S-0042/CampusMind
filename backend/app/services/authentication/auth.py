from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException,Request
from urllib.parse import quote
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
load_dotenv()
import os

SECRET_KEY = os.getenv("SECRET_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL")
ALGORITHM = "HS256"
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter()

config = Config(".env")
oauth = OAuth(config)
oauth.register(
    name='google',
    client_id = CLIENT_ID,
    client_secret = CLIENT_SECRET,
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs = {
        "scope":"openid email profile"
    }
)
    
#TO GENERATE JWT TOKEN
def create_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
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
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    
@router.get("/login")
async def login(request:Request):
    redirect_url = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request,redirect_url)
    
@router.get("/google/callback")
async def google_callback(request:Request,db:Session= Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token['userinfo']
    email = userinfo['email']
    username = userinfo.get('name') or email.split('@')[0]
    if not userinfo.get("email_verified"):
       return RedirectResponse(f"{FRONTEND_URL}/#error={quote('Google email not verified')}")
    try:
        user = db.query(User).filter(User.email_id == email).first()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Server side error"
        )
    if not user:
        user = User(username=username, email_id = email)
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
            jwt_token = create_token({"sub": str(user.id)})
            return RedirectResponse(f"{FRONTEND_URL}/#access_token={jwt_token}")
        except:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Server side error"
        )
    jwt_token = create_token({"sub": str(user.id)})
    return RedirectResponse(f"{FRONTEND_URL}/#access_token={jwt_token}")

    