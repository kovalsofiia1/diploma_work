from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.ticket_service import checkin_ticket, mark_ticket_used_async

router = APIRouter()


@router.post("/checkin")
def checkin(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Body: { qr_token: str }
    Returns: { status: 'ok' }
    """
    qr_token = payload.get("qr_token")
    if not qr_token:
        raise HTTPException(status_code=400, detail="qr_token is required")
    ok, reason, ticket = checkin_ticket(db, qr_token=qr_token, staff_user_id=user.id)
    if not ok:
        raise HTTPException(status_code=400, detail=reason or "Check-in failed")
    if ticket:
        background_tasks.add_task(mark_ticket_used_async, ticket.id)
    return {"status": "ok"}

