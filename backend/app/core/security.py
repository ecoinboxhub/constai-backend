from datetime import UTC, datetime, timedelta
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: str, role: str, company_id: Optional[int] = None) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {
        "sub": subject, 
        "role": role, 
        "company_id": company_id,
        "type": "access", 
        "exp": expires
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def create_refresh_token(subject: str, role: str, company_id: Optional[int] = None) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_refresh_expires_minutes)
    payload = {
        "sub": subject, 
        "role": role, 
        "company_id": company_id,
        "type": "refresh", 
        "exp": expires
    }
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm])

def decode_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def refresh_access_token(refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_refresh_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        sub = payload.get("sub", "")
        role = payload.get("role", "analyst")
        company_id = payload.get("company_id")
        return create_access_token(sub, role, company_id), create_refresh_token(sub, role, company_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Session expired")
