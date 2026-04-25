from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services import blockchain_service
from app.services.qr_service import decode_ticket_qr_token, generate_ticket_qr_token
from app.db.session import SessionLocal
from app.models.ticket import Ticket
from app.models.checkin import Checkin


def _compute_ticket_hash(ticket_id: str) -> str:
    """
    README-conformant hash:
    sha256(f"{ticket_id}{SECRET_KEY}")
    Returns 0x-prefixed hex string suitable for bytes32.
    """
    settings = get_settings()
    payload = f"{ticket_id}{settings.ticket_secret_key}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return "0x" + digest


def book_ticket(
    db: Session,
    *,
    event_id: int,
    user_id: int,
    quantity: int = 1,
    seat: Optional[str] = None,
    seat_id: Optional[str] = None,
) -> tuple[Ticket, dict]:
    now = datetime.now(timezone.utc)
    ticket_id = uuid4().hex
    code = f"TKT-{ticket_id[:10].upper()}"
    ticket_hash = _compute_ticket_hash(ticket_id)

    ticket = Ticket(
        ticket_id=ticket_id,
        code=code,
        event_id=event_id,
        user_id=user_id,
        quantity=quantity,
        seat_id=seat_id,
        seat=seat,
        token_id=None,
        ticket_hash=ticket_hash,
        status="pending_onchain",
        used=False,
        created_at=now.replace(tzinfo=None),
        updated_at=now.replace(tzinfo=None),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Use DB id as token_id for chain
    token_id = ticket.id
    ticket.token_id = token_id
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    qr_token = generate_ticket_qr_token(ticket_id=ticket.id, event_id=ticket.event_id)
    qr = {"qr_token": qr_token, "ticket_id": ticket.ticket_id}
    return ticket, qr


def mint_ticket_async(ticket_id: int) -> None:
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return
        if ticket.status not in ("pending_onchain", "reserved"):
            return

        token_id = ticket.token_id or ticket.id
        tx_hash = blockchain_service.mint_ticket(
            token_id=token_id,
            event_id=ticket.event_id,
            seat_id=ticket.seat_id,
            ticket_hash=ticket.ticket_hash,
        )
        ticket.tx_hash = tx_hash
        ticket.status = "confirmed_onchain"
        db.add(ticket)
        db.commit()
    except Exception:
        if "ticket" in locals() and ticket:
            ticket.status = "failed_onchain"
            db.add(ticket)
            db.commit()
    finally:
        db.close()


def verify_ticket_qr(db: Session, *, qr_token: str) -> tuple[bool, Optional[str], Optional[Ticket]]:
    try:
        payload = decode_ticket_qr_token(qr_token)
    except ValueError as exc:
        return False, str(exc), None

    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == payload["ticket_id"], Ticket.event_id == payload["event_id"])
        .first()
    )
    if not ticket:
        return False, "Ticket not found", None
    if ticket.used:
        return False, "Already used", ticket
    if ticket.status == "failed_onchain":
        return False, "On-chain confirmation failed", ticket
    return True, None, ticket


def checkin_ticket(db: Session, *, qr_token: str, staff_user_id: Optional[int]) -> tuple[bool, Optional[str], Optional[Ticket]]:
    ok, reason, ticket = verify_ticket_qr(db, qr_token=qr_token)
    if not ok or not ticket:
        return False, reason, ticket

    ticket.used = True
    ticket.status = "used"
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    ch = Checkin(ticket_id=ticket.id, staff_user_id=staff_user_id)
    db.add(ch)
    db.commit()

    return True, None, ticket


def mark_ticket_used_async(ticket_id: int) -> None:
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return
        tx_hash = blockchain_service.mark_used(ticket.token_id or ticket.id)
        ticket.tx_hash = tx_hash
        db.add(ticket)
        db.commit()
    except Exception:
        return
    finally:
        db.close()


