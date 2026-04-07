import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from dotenv import load_dotenv

from database import get_db_connection
from models import UserInDB

load_dotenv()

# Password hashing setup (Задание 6.2)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT setup (Задание 6.4, 6.5)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

# Security schemes
security_basic = HTTPBasic()
security_bearer = HTTPBearer()

# In-memory fake DB for tasks 6.2-6.5 (persists across requests)
fake_users_db: Dict[str, UserInDB] = {}

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user_basic(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with basic auth (Задание 6.2)"""
    # Check in fake DB first (for tasks 6.2-6.5)
    if username in fake_users_db:
        user = fake_users_db[username]
        if verify_password(password, user.hashed_password):
            return user
        return None
    
    # Then check in SQLite DB (for tasks 8.1+)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if row and verify_password(password, row["password"]):
            return UserInDB(username=row["username"], hashed_password=row["password"])
    
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token (Задание 6.4, 6.5)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user_basic(credentials: HTTPBasicCredentials = Depends(security_basic)) -> UserInDB:
    """Dependency for basic auth (Задание 6.2, 6.3)"""
    user = authenticate_user_basic(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

async def get_current_user_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> str:
    """Dependency for JWT auth (Задание 6.4, 6.5)"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    return username

def compare_strings(a: str, b: str) -> bool:
    """Timing-safe string comparison"""
    return secrets.compare_digest(a, b)