import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from . import models

load_dotenv()
SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me")
if os.getenv("APP_ENV", "development").lower() == "production" and (
    len(SECRET_KEY) < 32
    or SECRET_KEY in {"dev-only-change-me", "replace-this-with-a-long-random-secret"}
):
    raise RuntimeError("SECRET_KEY must contain at least 32 characters in production")
ALGORITHM="HS256"
EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
pwd_context=CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/api/auth/login")
def hash_password(password:str)->str: return pwd_context.hash(password)
def verify_password(password:str, hashed:str)->bool: return pwd_context.verify(password, hashed)
def create_access_token(subject:str, role:str, session_version: str | None = None):
    now = datetime.now(timezone.utc)
    exp=now+timedelta(minutes=EXPIRE_MINUTES)
    claims = {"sub":subject,"role":role,"iat":now,"exp":exp}
    if session_version is not None:
        claims["session_version"] = session_version
    return jwt.encode(
        claims,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
def authenticate_access_token(token: str, db: Session):
    err=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate":"Bearer"})
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        email=payload.get("sub")
    except JWTError: raise err
    if not email: raise err
    user=db.query(models.User).filter(models.User.email==email,models.User.is_active==True).first()
    if not user: raise err
    if payload.get("session_version", "") != user.session_version:
        raise err
    return user

def get_current_user(token:str=Depends(oauth2_scheme), db:Session=Depends(get_db)):
    return authenticate_access_token(token, db)

def require_roles(*roles):
    def checker(user:models.User=Depends(get_current_user)):
        if user.role not in roles: raise HTTPException(403,"Insufficient permissions")
        return user
    return checker
