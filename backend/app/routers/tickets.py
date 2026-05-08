from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.db.session import get_db
from app.models.event import Event
from app.models.ticket import Ticket
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.ticket import (
    TicketBookRequest,
    TicketBookBatchRequest,
    TicketBookBatchItem,
    TicketOut,
    BookResponse,
    BookBatchResponse,
    VerifyResponse,
    VerifyRequest,
    MyTicketsOut,
    OccupiedSeatsOut,
)
from app.services.ticket_service import (
    book_ticket,
    mint_ticket_async,
    verify_ticket_qr,
    send_ticket_pdf_email_async,
)
from app.services.qr_service import generate_ticket_qr_token


router = APIRouter()


def _active_ticket_filter():
    return Ticket.status.notin_(["failed_onchain", "cancelled"])


def _booked_places_for_event(db: Session, event_id: int) -> int:
    booked = (
        db.query(func.coalesce(func.sum(Ticket.quantity), 0))
        .filter(Ticket.event_id == event_id, _active_ticket_filter())
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
    can_use_qr = (not t.used) and (t.status != "cancelled")
    qr_token = generate_ticket_qr_token(ticket_id=t.id, event_id=t.event_id) if can_use_qr else None
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
        seat_id=t.seat_id,
        attendee_name=t.attendee_name,
        price_amount=t.price_amount,
        price_currency=t.price_currency,
        ticket_hash=t.ticket_hash,
        blockchain_tx_hash=t.tx_hash or t.blockchain_tx_hash,
        status=t.status,
        used=bool(t.used),
        created_at=t.created_at.isoformat() if t.created_at else None,
        qr_token=qr_token,
    )


def _event_seat_pricing(event: Event) -> dict[str, dict[str, int | str]]:
    raw = (event.additional or "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}

    if isinstance(payload, dict):
        rows = payload.get("seat_pricing")
    else:
        rows = None
    if not isinstance(rows, list):
        return {}

    pricing: dict[str, dict[str, int | str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        seat_id = str(row.get("seat_id") or "").strip()
        label = str(row.get("label") or "").strip()
        price_raw = row.get("price")
        if not seat_id or not label:
            continue
        try:
            price = int(price_raw)
        except (TypeError, ValueError):
            continue
        if price < 0:
            continue
        pricing[seat_id] = {"label": label, "price": price}
    return pricing


@router.post("/tickets/book", response_model=BookResponse, status_code=201)
def book(
    req: TicketBookRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookResponse:
    event = db.query(Event).filter(Event.id == req.event_id, Event.source_type == "INTERNAL").first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or not bookable")
    if event.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Event is cancelled")
    _ensure_places_available(db, event, req.quantity)
    seat_pricing = _event_seat_pricing(event)
    seat_info = seat_pricing.get(req.seat or "")
    seat_label = req.seat
    price_amount = None
    if seat_info:
        seat_label = str(seat_info["label"])
        price_amount = int(seat_info["price"])
    t, _qr = book_ticket(
        db,
        event_id=event.id,
        user_id=user.id,
        quantity=req.quantity,
        seat=seat_label,
        seat_id=req.seat,
        attendee_name=None,
        price_amount=price_amount,
        price_currency=event.price_currency,
    )
    background_tasks.add_task(mint_ticket_async, t.id)
    background_tasks.add_task(send_ticket_pdf_email_async, t.id)
    return BookResponse(ticket=_to_out(t, event))


@router.post("/tickets/book/batch", response_model=BookBatchResponse, status_code=201)
def book_batch(
    req: TicketBookBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookBatchResponse:
    event = db.query(Event).filter(Event.id == req.event_id, Event.source_type == "INTERNAL").first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or not bookable")
    if event.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Event is cancelled")

    items: list[TicketBookBatchItem] = []
    if getattr(req, "items", None):
        items = req.items
    else:
        names = [n.strip() for n in req.attendee_names if isinstance(n, str) and n.strip()]
        items = [TicketBookBatchItem(attendee_name=name) for name in names]
    if not items:
        raise HTTPException(status_code=400, detail="At least one attendee name is required")
    if len(items) > 10:
        raise HTTPException(status_code=400, detail="Too many tickets requested")
    _ensure_places_available(db, event, len(items))

    seat_pricing = _event_seat_pricing(event)
    seen_seat_ids: set[str] = set()

    tickets: list[TicketOut] = []
    for item in items:
        attendee_name = item.attendee_name.strip()
        seat_id = (item.seat_id or "").strip() or None
        seat_label = (item.seat_label or "").strip() or None
        seat_price_amount = None

        if seat_pricing:
            if not seat_id:
                raise HTTPException(status_code=400, detail="Seat is required for this event")
            if seat_id in seen_seat_ids:
                raise HTTPException(status_code=400, detail=f"Seat selected multiple times: {seat_id}")
            seen_seat_ids.add(seat_id)
            seat_info = seat_pricing.get(seat_id)
            if not seat_info:
                raise HTTPException(status_code=400, detail=f"Invalid seat selected: {seat_id}")
            seat_label = str(seat_info["label"])
            seat_price_amount = int(seat_info["price"])
            existing_ticket = (
                db.query(Ticket)
                .filter(Ticket.event_id == event.id, Ticket.seat_id == seat_id, _active_ticket_filter())
                .first()
            )
            if existing_ticket:
                raise HTTPException(status_code=409, detail=f"Seat already booked: {seat_label}")

        t, _qr = book_ticket(
            db,
            event_id=event.id,
            user_id=user.id,
            quantity=1,
            seat=(seat_label or attendee_name)[:64],
            seat_id=seat_id,
            attendee_name=attendee_name[:255],
            price_amount=seat_price_amount,
            price_currency=event.price_currency,
        )
        background_tasks.add_task(mint_ticket_async, t.id)
        background_tasks.add_task(send_ticket_pdf_email_async, t.id)
        tickets.append(_to_out(t, event))
    return BookBatchResponse(tickets=tickets)


@router.get("/tickets/events/{event_id}/occupied-seats", response_model=OccupiedSeatsOut)
def occupied_seats(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OccupiedSeatsOut:
    event = db.query(Event).filter(Event.id == event_id, Event.source_type == "INTERNAL").first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    rows = (
        db.query(Ticket.seat_id)
        .filter(
            Ticket.event_id == event_id,
            Ticket.seat_id.isnot(None),
            _active_ticket_filter(),
        )
        .all()
    )
    return OccupiedSeatsOut(
        seat_ids=[str(seat_id) for (seat_id,) in rows if seat_id]
    )


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


@router.delete("/tickets/me/{ticket_id}", status_code=204)
def cancel_my_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.user_id == user.id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.used:
        raise HTTPException(status_code=400, detail="Used ticket cannot be cancelled")
    if ticket.status == "cancelled":
        return None

    ticket.status = "cancelled"
    db.add(ticket)
    db.commit()
    return None


@router.post("/tickets/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResponse:
    ok, reason, ticket = verify_ticket_qr(db, qr_token=req.qr_token)
    if not ok:
        return VerifyResponse(status="INVALID", reason=reason, ticket=_to_out(ticket) if ticket else None)
    return VerifyResponse(status="VALID", ticket=_to_out(ticket))


