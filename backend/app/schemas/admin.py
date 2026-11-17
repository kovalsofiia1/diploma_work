from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.schemas.user import OrganizerApplicationAdminOut, UserStatus


class AuditLogEntryOut(BaseModel):
    id: int
    admin_user_id: Optional[int] = None
    admin_email: Optional[str] = None
    action: str
    target_type: str
    target_id: int
    details: Optional[dict[str, Any]] = None
    created_at: datetime


class AuditLogPage(BaseModel):
    items: List[AuditLogEntryOut]
    total: int


class AdminReasonRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=500)


class AdminApplicationsPage(BaseModel):
    items: List[OrganizerApplicationAdminOut]
    total: int


class AdminUserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    status: UserStatus
    provider: str
    is_active: bool
    blocked_reason: Optional[str] = None
    blocked_at: Optional[datetime] = None
    created_at: datetime
    # Events hidden (on block) or restored (on unblock) by this action
    affected_events: int = 0


class AdminUsersPage(BaseModel):
    items: List[AdminUserOut]
    total: int


class AdminEventOut(BaseModel):
    id: int
    uid: Optional[str] = None
    name: str
    city: Optional[str] = None
    start_date: Optional[datetime] = None
    source_type: str
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    status: str
    is_hidden: bool
    hidden_reason: Optional[str] = None
    hidden_at: Optional[datetime] = None
    created_by_user_id: Optional[int] = None
    created_by_email: Optional[str] = None


class AdminEventsPage(BaseModel):
    items: List[AdminEventOut]
    total: int


class AdminSummaryOut(BaseModel):
    pending_applications: int
    blocked_users: int
    hidden_events: int
