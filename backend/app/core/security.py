from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_minutes: Optional[int] = None, extra: Optional[dict[str, Any]] = None) -> str:
    if expires_minutes is None:
        expires_minutes = settings.access_token_expires_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode: dict[str, Any] = {"exp": expire, "sub": subject}
    if extra:
        to_encode.update(extra)
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

