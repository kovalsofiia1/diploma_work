from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import get_settings


def generate_ticket_qr_token(*, ticket_id: int, event_id: int) -> str:
    settings = get_settings()
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ticket_qr_expires_minutes)
    payload: dict[str, Any] = {
        "ticket_id": int(ticket_id),
        "event_id": int(event_id),
        "exp": expire_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_ticket_qr_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as exc:
        raise ValueError("QR token expired") from exc
    except InvalidTokenError as exc:
        raise ValueError("Invalid QR token") from exc

    ticket_id = decoded.get("ticket_id")
    event_id = decoded.get("event_id")
    if not isinstance(ticket_id, int) or not isinstance(event_id, int):
        raise ValueError("Invalid QR payload")
    return {"ticket_id": ticket_id, "event_id": event_id}
