from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.admin_audit_log import AdminAuditLog
from app.models.user import User
from app.routers.auth import get_current_admin
from app.schemas.admin import AuditLogEntryOut, AuditLogPage

# Every route here requires an authenticated admin; the check runs on the server.
router = APIRouter(dependencies=[Depends(get_current_admin)])


# --------------------------------------------------------------- audit log


@router.get("/audit-log", response_model=AuditLogPage)
def list_audit_log(
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    admin_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    query = db.query(AdminAuditLog, User.email).outerjoin(User, AdminAuditLog.admin_user_id == User.id)
    if action:
        query = query.filter(AdminAuditLog.action == action)
    if target_type:
        query = query.filter(AdminAuditLog.target_type == target_type)
    if admin_id:
        query = query.filter(AdminAuditLog.admin_user_id == admin_id)
    total = query.count()
    rows = (
        query.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return AuditLogPage(
        items=[
            AuditLogEntryOut(
                id=entry.id,
                admin_user_id=entry.admin_user_id,
                admin_email=email,
                action=entry.action,
                target_type=entry.target_type,
                target_id=entry.target_id,
                details=entry.details,
                created_at=entry.created_at,
            )
            for entry, email in rows
        ],
        total=total,
    )
