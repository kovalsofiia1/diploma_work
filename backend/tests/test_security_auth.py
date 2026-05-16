import asyncio

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import AuthProvider, User
from app.routers.auth import authenticate_user, get_current_user


def test_password_hash_is_verified():
    hashed = get_password_hash("StrongPassword123")

    assert hashed != "StrongPassword123"
    assert verify_password("StrongPassword123", hashed)
    assert not verify_password("WrongPassword123", hashed)


def test_create_access_token_contains_subject_and_extra_claims():
    settings = get_settings()

    token = create_access_token("42", expires_minutes=15, extra={"role": "user"})
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == "42"
    assert payload["role"] == "user"
    assert "exp" in payload


def test_authenticate_user_returns_none_for_wrong_password(db_session):
    user = User(
        email="user@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("CorrectPassword123"),
        provider=AuthProvider.local,
    )
    db_session.add(user)
    db_session.commit()

    assert authenticate_user(db_session, "user@example.com", "WrongPassword123") is None


def test_get_current_user_rejects_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(db=db_session, token="not-a-jwt"))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_get_current_user_rejects_unknown_user(db_session):
    token = create_access_token("999")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(db=db_session, token=token))

    assert exc_info.value.status_code == 401
