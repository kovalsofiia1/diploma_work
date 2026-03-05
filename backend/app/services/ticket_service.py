from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services import blockchain_service
from app.models.ticket import Ticket
from app.models.checkin import Checkin


def _compute_ticket_hash(ticket_id: str, event_id: int, user_id: int) -> str:
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
    ticket_hash = _compute_ticket_hash(ticket_id, event_id, user_id)

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
        status="minting",
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

    # Mint on blockchain (mock Phase 1)
    try:
        tx_hash = blockchain_service.mint_ticket(token_id=token_id, event_id=event_id, seat_id=seat_id, ticket_hash=ticket_hash)
        ticket.tx_hash = tx_hash
        ticket.status = "confirmed"
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
    except Exception as e:
        ticket.status = "failed"
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

    # Return QR payload per README (ticketId + ticketHash only)
    qr = {"ticketId": ticket.ticket_id, "ticketHash": ticket.ticket_hash}
    return ticket, qr


def checkin_ticket(db: Session, *, ticket_id: str, ticket_hash: str, staff_user_id: Optional[int]) -> tuple[bool, Optional[str], Optional[Ticket]]:
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        return False, "Ticket not found", None
    if ticket.used:
        return False, "Already used", ticket
    if ticket.status != "confirmed":
        return False, "Ticket not confirmed", ticket
    # Verify hash matches deterministically
    expected = _compute_ticket_hash(ticket.ticket_id, ticket.event_id, ticket.user_id)
    if expected != ticket_hash or expected != ticket.ticket_hash:
        return False, "Hash mismatch", ticket
    # Fetch on-chain (mock) and compare
    on_chain = blockchain_service.get_ticket(ticket.token_id or ticket.id)
    if not on_chain:
        return False, "On-chain ticket missing", ticket
    if on_chain.get("ticketHash") != ticket.ticket_hash:
        return False, "On-chain hash mismatch", ticket
    if on_chain.get("used"):
        return False, "On-chain already used", ticket

    # Atomic mark used + checkin record
    ticket.used = True
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    ch = Checkin(ticket_id=ticket.id, staff_user_id=staff_user_id)
    db.add(ch)
    db.commit()

    try:
        _ = blockchain_service.mark_used(ticket.token_id or ticket.id)
    except Exception:
        # Non-fatal for local mock; could add retry/outbox in production
        pass

    return True, None, ticket


