import jwt
import pytest

from app.core.config import get_settings
from app.services.qr_service import decode_ticket_qr_token, generate_ticket_qr_token


def test_generate_and_decode_ticket_qr_token():
    token = generate_ticket_qr_token(ticket_id=10, event_id=20)

    payload = decode_ticket_qr_token(token)

    assert payload == {"ticket_id": 10, "event_id": 20}


def test_decode_ticket_qr_token_rejects_invalid_token():
    with pytest.raises(ValueError, match="Invalid QR token"):
        decode_ticket_qr_token("invalid-token")


def test_decode_ticket_qr_token_rejects_invalid_payload():
    settings = get_settings()
    token = jwt.encode(
        {"ticket_id": "10", "event_id": 20},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(ValueError, match="Invalid QR payload"):
        decode_ticket_qr_token(token)
