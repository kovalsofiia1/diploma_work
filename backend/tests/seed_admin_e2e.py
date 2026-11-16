import os
from datetime import datetime, timedelta

from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal, create_all_tables
from app.models.admin_audit_log import AdminAuditLog
from app.models.event import Event
from app.models.organizer_application import OrganizerApplication, OrganizerApplicationStatus
from app.models.user import AuthProvider, User, UserStatus


ADMIN_EMAIL = "e2e-admin@example.com"
ADMIN_PASSWORD = "AdminPassword123!"
APPLICANT_EMAIL = "e2e-applicant@example.com"
USER_EMAIL = "e2e-user@example.com"
EVENT_UID = "e2e-admin-event"


def ensure_user(db, email: str, full_name: str, status: UserStatus) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(email=email)
    user.full_name = full_name
    user.hashed_password = get_password_hash(ADMIN_PASSWORD)
    user.provider = AuthProvider.local
    user.status = status
    user.is_active = True
    user.blocked_reason = None
    user.blocked_at = None
    db.add(user)
    db.flush()
    return user


def main() -> None:
    if os.environ.get("E2E_TEST_MODE") != "1":
        raise RuntimeError("Set E2E_TEST_MODE=1 to seed admin end-to-end data")
    url = make_url(get_settings().database_url)
    if (
        url.get_backend_name() != "postgresql"
        or url.database != "eventdb_test"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise RuntimeError("Refusing to seed data outside the local eventdb_test PostgreSQL database")

    create_all_tables()
    with SessionLocal() as db:
        admin = ensure_user(db, ADMIN_EMAIL, "E2E Admin", UserStatus.admin)
        applicant = ensure_user(db, APPLICANT_EMAIL, "E2E Applicant", UserStatus.user)
        ensure_user(db, USER_EMAIL, "E2E User", UserStatus.user)
        db.flush()

        db.query(AdminAuditLog).filter(AdminAuditLog.admin_user_id == admin.id).delete(
            synchronize_session=False
        )
        db.query(OrganizerApplication).filter(
            OrganizerApplication.user_id == applicant.id
        ).delete(synchronize_session=False)

        application = OrganizerApplication(
            user_id=applicant.id,
            organization_name="E2E Event Organization",
            contact_phone="+380501234567",
            motivation="End-to-end admin moderation test application.",
            status=OrganizerApplicationStatus.pending,
        )
        event = db.query(Event).filter(Event.uid == EVENT_UID).one_or_none()
        if event is None:
            event = Event(uid=EVENT_UID, name="E2E Admin Event")
        event.name = "E2E Admin Event"
        event.city = "Kyiv"
        event.startDate = datetime.utcnow() + timedelta(days=30)
        event.source_type = "INTERNAL"
        event.status = "ACTIVE"
        event.is_verified = True
        event.is_hidden = False
        event.hidden_reason = None
        event.hidden_at = None

        db.add_all([application, event])
        db.commit()


if __name__ == "__main__":
    main()
