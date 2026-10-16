from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


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
