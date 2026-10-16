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


# ----------------------------------------------------------- access control


ADMIN_ROUTES = [
    ("get", "/admin/audit-log"),
    ("post", "/admin/audit/tickets"),
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
