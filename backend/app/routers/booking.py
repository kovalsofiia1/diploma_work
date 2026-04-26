from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import Event
from app.models.ticket import Ticket
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.ticket_service import book_ticket, mint_ticket_async, send_ticket_pdf_email_async

router = APIRouter()


@router.post("/book")
def book(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Body: { event_id: int, seat_id?: str, seat?: str, quantity?: int }
    Returns: { qr_token, ticket_id }
    """
    event_id = int(payload.get("event_id", 0))
    if not event_id:
        raise HTTPException(status_code=400, detail="event_id is required")
    seat_id = payload.get("seat_id")
    seat = payload.get("seat")
    quantity = int(payload.get("quantity", 1))

    event = db.query(Event).filter(Event.id == event_id, Event.source_type == "INTERNAL").first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or not bookable")
    if event.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Event is cancelled")

    # Enforce unique seat per event if seat_id provided
    if seat_id:
        exists = db.query(Ticket).filter(Ticket.event_id == event_id, Ticket.seat_id == seat_id).first()
        if exists:
            raise HTTPException(status_code=409, detail="Seat already booked")

    ticket, qr = book_ticket(db, event_id=event_id, user_id=user.id, quantity=quantity, seat=seat, seat_id=seat_id)
    background_tasks.add_task(mint_ticket_async, ticket.id)
    background_tasks.add_task(send_ticket_pdf_email_async, ticket.id)
    return qr

