from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.models.user import User


def log_admin_action(
    db: Session,
    *,
    admin: User,
    action: str,
    target_type: str,
    target_id: int,
    details: Optional[dict[str, Any]] = None,
) -> AdminAuditLog:
    """Stage an audit record in the current transaction.

    The caller commits it together with the change itself, so a failed
    operation is rolled back along with its log entry.
    """
    entry = AdminAuditLog(
        admin_user_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details or None,
    )
    db.add(entry)
    return entry
