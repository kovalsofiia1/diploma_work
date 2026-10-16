import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, get_password_hash
from app.db.session import Base, get_db
from app.models import admin_audit_log, checkin, event, organizer_application, ticket, user  # noqa: F401
from app.models.admin_audit_log import AdminAuditLog
from app.models.organizer_application import OrganizerApplication, OrganizerApplicationStatus
from app.models.user import AuthProvider, User, UserStatus
from app.routers import admin, auth, events, tickets


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    yield factory
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def client(session_factory):
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    app.include_router(events.router)
    app.include_router(tickets.router)
    app.include_router(admin.router, prefix="/admin")

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def make_user(db, email, *, status=UserStatus.user, password="Password123", is_active=True):
    u = User(
        email=email,
        full_name=email.split("@")[0],
        hashed_password=get_password_hash(password),
        provider=AuthProvider.local,
        status=status,
        is_active=is_active,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def auth_headers(u):
    return {"Authorization": f"Bearer {create_access_token(str(u.id))}"}


def audit_actions(db):
    db.expire_all()
    return [row.action for row in db.query(AdminAuditLog).order_by(AdminAuditLog.id).all()]


# ----------------------------------------------------------- access control


ADMIN_ROUTES = [
    ("get", "/admin/audit-log"),
    ("post", "/admin/audit/tickets"),
    ("get", "/admin/organizer-applications"),
]


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_admin_routes_require_authentication(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_admin_routes_reject_non_admin(client, db, method, path):
    regular = make_user(db, "user@example.com", status=UserStatus.verified_user)
    resp = getattr(client, method)(path, headers=auth_headers(regular))
    assert resp.status_code == 403


def test_admin_can_open_admin_routes(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    resp = client.get("/admin/audit-log", headers=auth_headers(adm))
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}


def test_forged_token_is_rejected(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    forged = jwt.encode({"sub": str(adm.id)}, "not-the-real-secret", algorithm="HS256")
    resp = client.get("/admin/audit-log", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_admin_emails_setting_grants_admin_on_login(client, db, monkeypatch):
    monkeypatch.setattr(auth.settings, "admin_emails", "Boss@Example.com")
    make_user(db, "boss@example.com")
    resp = client.post("/auth/login", data={"username": "boss@example.com", "password": "Password123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert client.get("/admin/audit-log", headers={"Authorization": f"Bearer {token}"}).status_code == 200


# ------------------------------------------------- organizer applications


APPLICATION = {
    "organization_name": "Event Org",
    "contact_phone": "+380501234567",
    "motivation": "We run concerts in Kyiv and want to sell tickets here.",
}


def test_submitted_application_waits_for_review(client, db):
    applicant = make_user(db, "org@example.com")
    resp = client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["can_create_events"] is False
    db.refresh(applicant)
    assert applicant.status == UserStatus.user


def test_pending_applicant_cannot_create_events(client, db):
    applicant = make_user(db, "org@example.com")
    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))
    mine = client.get("/auth/me/organizer-application", headers=auth_headers(applicant)).json()
    assert mine["status"] == "pending"
    assert mine["can_create_events"] is False


def test_admin_approves_application(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    applicant = make_user(db, "org@example.com")
    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))

    listed = client.get("/admin/organizer-applications?status=pending", headers=auth_headers(adm)).json()
    assert listed["total"] == 1
    app_id = listed["items"][0]["id"]

    resp = client.post(f"/admin/organizer-applications/{app_id}/approve", headers=auth_headers(adm))
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    db.refresh(applicant)
    assert applicant.status == UserStatus.verified_user
    mine = client.get("/auth/me/organizer-application", headers=auth_headers(applicant)).json()
    assert mine["status"] == "approved"
    assert audit_actions(db) == ["organizer_application.approved"]


def test_admin_rejects_application_with_reason(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    applicant = make_user(db, "org@example.com")
    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))
    app_id = db.query(OrganizerApplication).one().id

    resp = client.post(
        f"/admin/organizer-applications/{app_id}/reject",
        json={"reason": "No proof of experience"},
        headers=auth_headers(adm),
    )
    assert resp.status_code == 200

    mine = client.get("/auth/me/organizer-application", headers=auth_headers(applicant)).json()
    assert mine["status"] == "rejected"
    assert mine["rejection_reason"] == "No proof of experience"
    db.refresh(applicant)
    assert applicant.status == UserStatus.user
    assert audit_actions(db) == ["organizer_application.rejected"]


def test_reject_requires_reason(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    applicant = make_user(db, "org@example.com")
    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))
    app_id = db.query(OrganizerApplication).one().id

    resp = client.post(f"/admin/organizer-applications/{app_id}/reject", json={"reason": ""}, headers=auth_headers(adm))
    assert resp.status_code == 422
    assert audit_actions(db) == []


def test_reviewed_application_cannot_be_reviewed_again(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    applicant = make_user(db, "org@example.com")
    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))
    app_id = db.query(OrganizerApplication).one().id

    assert client.post(f"/admin/organizer-applications/{app_id}/approve", headers=auth_headers(adm)).status_code == 200
    second = client.post(
        f"/admin/organizer-applications/{app_id}/reject", json={"reason": "Changed mind"}, headers=auth_headers(adm)
    )
    assert second.status_code == 409
    # The failed operation must not appear in the audit log
    assert audit_actions(db) == ["organizer_application.approved"]


def test_resubmission_after_rejection_creates_new_application(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    applicant = make_user(db, "org@example.com")
    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))
    first_id = db.query(OrganizerApplication).one().id
    client.post(f"/admin/organizer-applications/{first_id}/reject", json={"reason": "Too vague"}, headers=auth_headers(adm))

    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))
    db.expire_all()
    statuses = [a.status for a in db.query(OrganizerApplication).order_by(OrganizerApplication.id)]
    assert statuses == [OrganizerApplicationStatus.rejected, OrganizerApplicationStatus.pending]


def test_moderation_routes_are_no_longer_under_auth(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    assert client.get("/auth/organizer-applications", headers=auth_headers(adm)).status_code == 404
