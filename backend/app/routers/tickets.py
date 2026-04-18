import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.event import Event
from app.models.ticket import Ticket
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.ticket import (
    TicketBookRequest,
    TicketBookBatchRequest,
    TicketOut,
    BookResponse,
    BookBatchResponse,
    VerifyResponse,
    MyTicketsOut,
)
from app.services.ticket_service import book_ticket
from app.core.config import get_settings
from app.services import blockchain_service


router = APIRouter()


def _booked_places_for_event(db: Session, event_id: int) -> int:
    booked = (
        db.query(func.coalesce(func.sum(Ticket.quantity), 0))
        .filter(Ticket.event_id == event_id, Ticket.status != "failed")
        .scalar()
    )
    return int(booked or 0)


def _ensure_places_available(db: Session, event: Event, requested_count: int) -> None:
    total_places = event.total_places
    if total_places is None:
        return
    booked = _booked_places_for_event(db, event.id)
    available = max(total_places - booked, 0)
    if requested_count > available:
        raise HTTPException(
            status_code=409,
            detail=f"Only {available} places left",
        )


def _to_out(t: Ticket, event: Event | None = None) -> TicketOut:
    return TicketOut(
        id=t.id,
        ticket_id=t.ticket_id,
        code=t.code,
        event_id=t.event_id,
        event_name=event.name if event else None,
        event_start_date=event.startDate.isoformat() if event and event.startDate else None,
        event_location=event.location_name if event else None,
        event_city=event.city if event else None,
        user_id=t.user_id,
        quantity=t.quantity,
        seat=t.seat,
        ticket_hash=t.ticket_hash,
        blockchain_tx_hash=t.tx_hash or t.blockchain_tx_hash,
        status=t.status,
        used=bool(t.used),
        created_at=t.created_at.isoformat() if t.created_at else None,
    )


@router.post("/tickets/book", response_model=BookResponse, status_code=201)
def book(req: TicketBookRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> BookResponse:
    event = db.query(Event).filter(Event.id == req.event_id, Event.source_type == "INTERNAL").first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or not bookable")
    if event.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Event is cancelled")
    _ensure_places_available(db, event, req.quantity)
    t, _qr = book_ticket(db, event_id=event.id, user_id=user.id, quantity=req.quantity, seat=req.seat, seat_id=None)
    return BookResponse(ticket=_to_out(t, event))


@router.post("/tickets/book/batch", response_model=BookBatchResponse, status_code=201)
def book_batch(
    req: TicketBookBatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookBatchResponse:
    event = db.query(Event).filter(Event.id == req.event_id, Event.source_type == "INTERNAL").first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or not bookable")
    if event.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Event is cancelled")

    names = [n.strip() for n in req.attendee_names if isinstance(n, str) and n.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="At least one attendee name is required")
    if len(names) > 10:
        raise HTTPException(status_code=400, detail="Too many tickets requested")
    _ensure_places_available(db, event, len(names))

    tickets: list[TicketOut] = []
    for name in names:
        t, _qr = book_ticket(
            db,
            event_id=event.id,
            user_id=user.id,
            quantity=1,
            seat=name[:64],  # temporary attendee marker until dedicated field is introduced
            seat_id=None,
        )
        tickets.append(_to_out(t, event))
    return BookBatchResponse(tickets=tickets)


@router.get("/tickets/me", response_model=MyTicketsOut)
def my_tickets(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> MyTicketsOut:
    rows = db.query(Ticket).filter(Ticket.user_id == user.id).order_by(Ticket.created_at.desc()).all()
    event_ids = {t.event_id for t in rows}
    events = (
        db.query(Event)
        .filter(Event.id.in_(event_ids))
        .all()
        if event_ids
        else []
    )
    event_map = {e.id: e for e in events}
    return MyTicketsOut(items=[_to_out(t, event_map.get(t.event_id)) for t in rows])


@router.get("/tickets/verify/{ticket_id}", response_model=VerifyResponse)
def verify(ticket_id: str, db: Session = Depends(get_db)) -> VerifyResponse:
    t = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not t:
        return VerifyResponse(status="INVALID", reason="Ticket not found")
    # Recompute hash per current scheme
    settings = get_settings()
    expected = "0x" + hashlib.sha256(f"{t.ticket_id}{settings.ticket_secret_key}".encode("utf-8")).hexdigest()
    if expected != t.ticket_hash:
        return VerifyResponse(status="INVALID", reason="Hash mismatch", ticket=_to_out(t))
    on_chain = blockchain_service.get_ticket(t.token_id or t.id)
    if not on_chain:
        return VerifyResponse(status="INVALID", reason="On-chain missing", ticket=_to_out(t))
    if on_chain.get("ticketHash") != t.ticket_hash:
        return VerifyResponse(status="INVALID", reason="On-chain hash mismatch", ticket=_to_out(t))
    if t.status not in ("ACTIVE", "confirmed"):
        return VerifyResponse(status="INVALID", reason="Ticket not confirmed/active", ticket=_to_out(t))
    return VerifyResponse(status="VALID", ticket=_to_out(t))


