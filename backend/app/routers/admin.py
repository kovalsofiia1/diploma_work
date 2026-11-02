from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.admin_audit_log import AdminAction, AdminAuditLog
from app.models.organizer_application import OrganizerApplication
from app.models.organizer_application import OrganizerApplicationStatus as ApplicationRecordStatus
from app.models.user import User, UserStatus
from app.routers.auth import get_current_admin
from app.schemas.admin import (
    AdminApplicationsPage,
    AdminReasonRequest,
    AdminUserOut,
    AdminUsersPage,
    AuditLogEntryOut,
    AuditLogPage,
)
from app.schemas.user import OrganizerApplicationAdminOut, OrganizerApplicationStatus
from app.services.audit_service import log_admin_action

# Every route here requires an authenticated admin; the check runs on the server.
router = APIRouter(dependencies=[Depends(get_current_admin)])


def _like(term: str) -> str:
    return f"%{term.strip()}%"


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


# ---------------------------------------------------- organizer applications


def _application_out(rec: OrganizerApplication, user: User) -> OrganizerApplicationAdminOut:
    return OrganizerApplicationAdminOut(
        id=rec.id,
        user_id=user.id,
        user_email=user.email,
        user_full_name=user.full_name,
        organization_name=rec.organization_name,
        contact_phone=rec.contact_phone,
        motivation=rec.motivation,
        experience=rec.experience,
        status=OrganizerApplicationStatus(rec.status.value),
        submitted_at=rec.submitted_at,
        reviewed_at=rec.reviewed_at,
        rejection_reason=rec.rejection_reason,
    )


def _get_pending_application(db: Session, application_id: int) -> tuple[OrganizerApplication, User]:
    row = (
        db.query(OrganizerApplication, User)
        .join(User, OrganizerApplication.user_id == User.id)
        .filter(OrganizerApplication.id == application_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    rec, user = row
    if rec.status != ApplicationRecordStatus.pending:
        raise HTTPException(status_code=409, detail="Application has already been reviewed")
    return rec, user


@router.get("/organizer-applications", response_model=AdminApplicationsPage)
def list_applications(
    status: Optional[ApplicationRecordStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> AdminApplicationsPage:
    query = db.query(OrganizerApplication, User).join(User, OrganizerApplication.user_id == User.id)
    if status:
        query = query.filter(OrganizerApplication.status == status)
    total = query.count()
    rows = query.order_by(OrganizerApplication.submitted_at.desc()).offset(skip).limit(limit).all()
    return AdminApplicationsPage(items=[_application_out(rec, usr) for rec, usr in rows], total=total)


@router.post("/organizer-applications/{application_id}/approve", response_model=OrganizerApplicationAdminOut)
def approve_application(
    application_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> OrganizerApplicationAdminOut:
    rec, user = _get_pending_application(db, application_id)

    rec.status = ApplicationRecordStatus.approved
    rec.reviewed_at = datetime.utcnow()
    rec.rejection_reason = None
    if user.status != UserStatus.admin:
        user.status = UserStatus.verified_user
    log_admin_action(
        db,
        admin=admin,
        action=AdminAction.application_approved,
        target_type="organizer_application",
        target_id=rec.id,
        details={"user_id": user.id, "user_email": user.email},
    )
    db.commit()
    db.refresh(rec)
    return _application_out(rec, user)


@router.post("/organizer-applications/{application_id}/reject", response_model=OrganizerApplicationAdminOut)
def reject_application(
    application_id: int,
    payload: AdminReasonRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> OrganizerApplicationAdminOut:
    rec, user = _get_pending_application(db, application_id)

    reason = payload.reason.strip()
    rec.status = ApplicationRecordStatus.rejected
    rec.reviewed_at = datetime.utcnow()
    rec.rejection_reason = reason
    log_admin_action(
        db,
        admin=admin,
        action=AdminAction.application_rejected,
        target_type="organizer_application",
        target_id=rec.id,
        details={"user_id": user.id, "user_email": user.email, "reason": reason},
    )
    db.commit()
    db.refresh(rec)
    return _application_out(rec, user)


# ------------------------------------------------------------------- users


def _user_out(u: User) -> AdminUserOut:
    return AdminUserOut(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        status=u.status.value,
        provider=u.provider.value,
        is_active=u.is_active,
        blocked_reason=u.blocked_reason,
        blocked_at=u.blocked_at,
        created_at=u.created_at,
    )


def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users", response_model=AdminUsersPage)
def list_users(
    search: Optional[str] = None,
    status: Optional[UserStatus] = None,
    blocked: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> AdminUsersPage:
    query = db.query(User)
    if search and search.strip():
        query = query.filter(or_(User.email.ilike(_like(search)), User.full_name.ilike(_like(search))))
    if status:
        query = query.filter(User.status == status)
    if blocked is not None:
        query = query.filter(User.is_active.is_(not blocked))
    total = query.count()
    rows = query.order_by(User.created_at.desc(), User.id.desc()).offset(skip).limit(limit).all()
    return AdminUsersPage(items=[_user_out(u) for u in rows], total=total)


@router.post("/users/{user_id}/block", response_model=AdminUserOut)
def block_user(
    user_id: int,
    payload: AdminReasonRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserOut:
    user = _get_user(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot block yourself")
    if user.status == UserStatus.admin:
        raise HTTPException(status_code=400, detail="Administrators cannot be blocked")
    if not user.is_active:
        raise HTTPException(status_code=409, detail="User is already blocked")

    reason = payload.reason.strip()
    user.is_active = False
    user.blocked_reason = reason
    user.blocked_at = datetime.utcnow()
    log_admin_action(
        db,
        admin=admin,
        action=AdminAction.user_blocked,
        target_type="user",
        target_id=user.id,
        details={"user_email": user.email, "reason": reason},
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/users/{user_id}/unblock", response_model=AdminUserOut)
def unblock_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserOut:
    user = _get_user(db, user_id)
    if user.is_active:
        raise HTTPException(status_code=409, detail="User is not blocked")

    previous_reason = user.blocked_reason
    user.is_active = True
    user.blocked_reason = None
    user.blocked_at = None
    log_admin_action(
        db,
        admin=admin,
        action=AdminAction.user_unblocked,
        target_type="user",
        target_id=user.id,
        details={"user_email": user.email, "previous_reason": previous_reason},
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)
