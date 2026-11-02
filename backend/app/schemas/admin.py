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


class AdminUsersPage(BaseModel):
    items: List[AdminUserOut]
    total: int
