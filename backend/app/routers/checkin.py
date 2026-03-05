from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.ticket_service import checkin_ticket

router = APIRouter()


@router.post("/checkin")
def checkin(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Body: { ticketId: str, ticketHash: str }
    Returns: { status: 'ok' }
    """
    ticket_id = payload.get("ticketId")
    ticket_hash = payload.get("ticketHash")
    if not ticket_id or not ticket_hash:
        raise HTTPException(status_code=400, detail="ticketId and ticketHash are required")
    ok, reason, _ = checkin_ticket(db, ticket_id=ticket_id, ticket_hash=ticket_hash, staff_user_id=user.id)
    if not ok:
        raise HTTPException(status_code=400, detail=reason or "Check-in failed")
    return {"status": "ok"}

