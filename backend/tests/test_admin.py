import os
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, get_password_hash
from app.db.session import Base, get_db
from app.models import admin_audit_log, checkin, event, organizer_application, ticket, user  # noqa: F401
from app.models.admin_audit_log import AdminAuditLog
from app.models.event import Event
from app.models.organizer_application import OrganizerApplication, OrganizerApplicationStatus
from app.models.user import AuthProvider, User, UserFavoriteEvent, UserStatus
from app.routers import admin, auth, events, tickets


@pytest.fixture()
def session_factory():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("Set TEST_DATABASE_URL to the dedicated eventdb_test database")

    url = make_url(database_url)
    if (
        url.get_backend_name() != "postgresql"
        or url.database != "eventdb_test"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
    ):
        pytest.fail("Refusing to run admin tests outside the local eventdb_test PostgreSQL database")

    engine = create_engine(url, future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    try:
        yield factory
    finally:
        try:
            Base.metadata.drop_all(bind=engine)
        finally:
            engine.dispose()


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


def make_event(db, name="Concert", **kwargs):
    e = Event(
        name=name,
        city="Kyiv",
        startDate=datetime.utcnow() + timedelta(days=10),
        source_type=kwargs.pop("source_type", "INTERNAL"),
        **kwargs,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def audit_actions(db):
    db.expire_all()
    return [row.action for row in db.query(AdminAuditLog).order_by(AdminAuditLog.id).all()]


# ----------------------------------------------------------- access control


ADMIN_ROUTES = [
    ("get", "/admin/audit-log"),
    ("post", "/admin/audit/tickets"),
    ("get", "/admin/organizer-applications"),
    ("get", "/admin/users"),
    ("get", "/admin/events"),
    ("get", "/admin/summary"),
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


def test_admin_lists_applications_by_status_with_pagination(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    applicants = [make_user(db, f"org{index}@example.com") for index in range(3)]
    for applicant in applicants:
        response = client.post(
            "/auth/me/organizer-application",
            json=APPLICATION,
            headers=auth_headers(applicant),
        )
        assert response.status_code == 200

    rejected_application = (
        db.query(OrganizerApplication)
        .filter(OrganizerApplication.user_id == applicants[0].id)
        .one()
    )
    rejected = client.post(
        f"/admin/organizer-applications/{rejected_application.id}/reject",
        json={"reason": "Insufficient information"},
        headers=auth_headers(adm),
    )
    assert rejected.status_code == 200

    pending = client.get(
        "/admin/organizer-applications?status=pending",
        headers=auth_headers(adm),
    ).json()
    first_page = client.get(
        "/admin/organizer-applications?status=pending&skip=0&limit=1",
        headers=auth_headers(adm),
    ).json()
    second_page = client.get(
        "/admin/organizer-applications?status=pending&skip=1&limit=1",
        headers=auth_headers(adm),
    ).json()
    rejected_page = client.get(
        "/admin/organizer-applications?status=rejected",
        headers=auth_headers(adm),
    ).json()

    assert pending["total"] == 2
    assert first_page["total"] == second_page["total"] == 2
    assert len(first_page["items"]) == len(second_page["items"]) == 1
    assert first_page["items"][0]["id"] != second_page["items"][0]["id"]
    assert all(item["status"] == "pending" for item in first_page["items"] + second_page["items"])
    assert rejected_page["total"] == 1
    assert rejected_page["items"][0]["status"] == "rejected"


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


# ------------------------------------------------------------------ blocking


def test_blocked_user_cannot_log_in(client, db):
    make_user(db, "spam@example.com", is_active=False)
    resp = client.post("/auth/login", data={"username": "spam@example.com", "password": "Password123"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Account is blocked"


def test_token_issued_before_blocking_stops_working(client, db):
    violator = make_user(db, "spam@example.com")
    headers = auth_headers(violator)
    assert client.get("/auth/me", headers=headers).status_code == 200

    violator.is_active = False
    db.commit()

    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Account is blocked"


# ------------------------------------------------------------------ users


def test_admin_lists_and_searches_users(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    make_user(db, "alice@example.com")
    make_user(db, "bob@example.com")

    all_users = client.get("/admin/users", headers=auth_headers(adm)).json()
    assert all_users["total"] == 3
    found = client.get("/admin/users?search=alice", headers=auth_headers(adm)).json()
    assert [u["email"] for u in found["items"]] == ["alice@example.com"]


def test_admin_filters_and_paginates_users(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    blocked_users = [
        make_user(db, f"blocked{index}@example.com", status=UserStatus.verified_user)
        for index in range(2)
    ]
    active_user = make_user(db, "active@example.com", status=UserStatus.verified_user)
    for user in blocked_users:
        response = client.post(
            f"/admin/users/{user.id}/block",
            json={"reason": "Policy violation"},
            headers=auth_headers(adm),
        )
        assert response.status_code == 200

    def get_users(**params):
        response = client.get("/admin/users", params=params, headers=auth_headers(adm))
        assert response.status_code == 200, response.text
        return response.json()

    first_page = get_users(status=UserStatus.verified_user.value, blocked=True, skip=0, limit=1)
    second_page = get_users(status=UserStatus.verified_user.value, blocked=True, skip=1, limit=1)
    active = get_users(status=UserStatus.verified_user.value, blocked=False)

    assert first_page["total"] == second_page["total"] == 2
    assert len(first_page["items"]) == len(second_page["items"]) == 1
    assert first_page["items"][0]["id"] != second_page["items"][0]["id"]
    assert all(not page["items"][0]["is_active"] for page in (first_page, second_page))
    assert active["total"] == 1
    assert active["items"][0]["id"] == active_user.id


def test_blocked_user_loses_access_immediately(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    violator = make_user(db, "spam@example.com")
    old_token_headers = auth_headers(violator)
    assert client.get("/auth/me", headers=old_token_headers).status_code == 200

    resp = client.post(f"/admin/users/{violator.id}/block", json={"reason": "Spam"}, headers=auth_headers(adm))
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["blocked_reason"] == "Spam"

    # Previously issued token stops working
    me = client.get("/auth/me", headers=old_token_headers)
    assert me.status_code == 403
    assert me.json()["detail"] == "Account is blocked"
    # And a fresh login is refused
    login = client.post("/auth/login", data={"username": "spam@example.com", "password": "Password123"})
    assert login.status_code == 403
    assert audit_actions(db) == ["user.blocked"]


def test_unblocked_user_can_log_in_again(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    violator = make_user(db, "spam@example.com")
    client.post(f"/admin/users/{violator.id}/block", json={"reason": "Spam"}, headers=auth_headers(adm))

    assert client.post(f"/admin/users/{violator.id}/unblock", headers=auth_headers(adm)).status_code == 200
    login = client.post("/auth/login", data={"username": "spam@example.com", "password": "Password123"})
    assert login.status_code == 200
    assert audit_actions(db) == ["user.blocked", "user.unblocked"]


def test_admin_cannot_block_self_or_other_admins(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    other = make_user(db, "admin2@example.com", status=UserStatus.admin)

    assert client.post(f"/admin/users/{adm.id}/block", json={"reason": "Oops"}, headers=auth_headers(adm)).status_code == 400
    assert client.post(f"/admin/users/{other.id}/block", json={"reason": "Oops"}, headers=auth_headers(adm)).status_code == 400
    assert audit_actions(db) == []


def test_block_requires_reason(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    violator = make_user(db, "spam@example.com")
    resp = client.post(f"/admin/users/{violator.id}/block", json={"reason": ""}, headers=auth_headers(adm))
    assert resp.status_code == 422


def test_blocking_already_blocked_user_conflicts_without_duplicate_audit(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    user = make_user(db, "spam@example.com")
    headers = auth_headers(adm)

    first = client.post(
        f"/admin/users/{user.id}/block",
        json={"reason": "Spam"},
        headers=headers,
    )
    second = client.post(
        f"/admin/users/{user.id}/block",
        json={"reason": "Repeated report"},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert audit_actions(db) == ["user.blocked"]


# -------------------------------------------------------------- audit log


def test_audit_log_records_actor_action_target_and_time(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    violator = make_user(db, "spam@example.com")
    client.post(f"/admin/users/{violator.id}/block", json={"reason": "Spam"}, headers=auth_headers(adm))

    log = client.get("/admin/audit-log", headers=auth_headers(adm)).json()
    assert log["total"] == 1
    entry = log["items"][0]
    assert entry["admin_email"] == "admin@example.com"
    assert entry["action"] == "user.blocked"
    assert entry["target_type"] == "user"
    assert entry["target_id"] == violator.id
    assert entry["details"]["reason"] == "Spam"
    assert entry["created_at"]


def test_audit_log_filters_and_paginates_entries(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    other_admin = make_user(db, "other-admin@example.com", status=UserStatus.admin)
    first_user = make_user(db, "first@example.com")
    second_user = make_user(db, "second@example.com")
    other_admin_user = make_user(db, "third@example.com")

    for user in (first_user, second_user):
        response = client.post(
            f"/admin/users/{user.id}/block",
            json={"reason": "Spam"},
            headers=auth_headers(adm),
        )
        assert response.status_code == 200
    other_response = client.post(
        f"/admin/users/{other_admin_user.id}/block",
        json={"reason": "Spam"},
        headers=auth_headers(other_admin),
    )
    assert other_response.status_code == 200

    filtered = client.get(
        f"/admin/audit-log?action=user.blocked&target_type=user&admin_id={adm.id}",
        headers=auth_headers(adm),
    ).json()
    page = client.get(
        f"/admin/audit-log?action=user.blocked&target_type=user&admin_id={adm.id}&skip=1&limit=1",
        headers=auth_headers(adm),
    ).json()

    assert filtered["total"] == page["total"] == 2
    assert len(page["items"]) == 1
    assert page["items"][0]["admin_user_id"] == adm.id
    assert page["items"][0]["id"] == filtered["items"][1]["id"]


# ------------------------------------------------------------------- events


def public_event_ids(client, headers=None):
    resp = client.get("/events/all", headers=headers or {})
    assert resp.status_code == 200
    return {item["id"] for item in resp.json()["items"]}


def test_admin_filters_and_paginates_events(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    matching_events = [
        make_event(db, f"Hidden festival {index}", source_type="EXTERNAL", is_hidden=True)
        for index in range(2)
    ]
    make_event(db, "Visible festival", source_type="EXTERNAL")
    make_event(db, "Hidden internal concert", source_type="INTERNAL", is_hidden=True)
    headers = auth_headers(adm)

    first_page = client.get(
        "/admin/events?search=Hidden&hidden=true&source_type=EXTERNAL&skip=0&limit=1",
        headers=headers,
    ).json()
    second_page = client.get(
        "/admin/events?search=Hidden&hidden=true&source_type=EXTERNAL&skip=1&limit=1",
        headers=headers,
    ).json()

    assert first_page["total"] == second_page["total"] == 2
    assert len(first_page["items"]) == len(second_page["items"]) == 1
    assert first_page["items"][0]["id"] != second_page["items"][0]["id"]
    assert {first_page["items"][0]["id"], second_page["items"][0]["id"]} == {
        event.id for event in matching_events
    }


def test_hidden_event_is_excluded_from_public_results(client, db):
    fake = make_event(db, "Fake concert", uid="fake-1", is_hidden=True)
    real = make_event(db, "Real concert", uid="real-1")

    assert public_event_ids(client) == {real.id}
    assert client.get("/events/lookup/fake-1").status_code == 404
    assert client.get("/events/lookup/real-1").status_code == 200
    assert fake.id not in public_event_ids(client)


def test_hidden_event_stays_visible_to_admin_and_owner(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    owner = make_user(db, "org@example.com", status=UserStatus.verified_user)
    make_event(db, "Fake concert", uid="fake-1", created_by_user_id=owner.id, is_hidden=True)

    assert client.get("/events/lookup/fake-1", headers=auth_headers(adm)).status_code == 200
    owner_view = client.get("/events/lookup/fake-1", headers=auth_headers(owner))
    assert owner_view.status_code == 200
    assert owner_view.json()["is_hidden"] is True


def test_hidden_event_cannot_be_booked(client, db):
    buyer = make_user(db, "buyer@example.com")
    fake = make_event(db, "Fake concert", total_places=100, is_hidden=True)

    resp = client.post("/tickets/book", json={"event_id": fake.id, "quantity": 1}, headers=auth_headers(buyer))
    assert resp.status_code == 404


def test_admin_hides_event_with_reason(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    fake = make_event(db, "Fake concert", uid="fake-1")
    real = make_event(db, "Real concert", uid="real-1")

    resp = client.post(f"/admin/events/{fake.id}/hide", json={"reason": "Wrong date and venue"}, headers=auth_headers(adm))
    assert resp.status_code == 200
    assert resp.json()["is_hidden"] is True
    assert resp.json()["hidden_reason"] == "Wrong date and venue"

    assert public_event_ids(client) == {real.id}
    hidden = client.get("/admin/events?hidden=true", headers=auth_headers(adm)).json()
    assert [e["id"] for e in hidden["items"]] == [fake.id]
    assert audit_actions(db) == ["event.hidden"]


def test_hiding_twice_conflicts_and_is_not_logged(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    fake = make_event(db, "Fake concert")
    client.post(f"/admin/events/{fake.id}/hide", json={"reason": "Wrong date"}, headers=auth_headers(adm))

    again = client.post(f"/admin/events/{fake.id}/hide", json={"reason": "Wrong date"}, headers=auth_headers(adm))
    assert again.status_code == 409
    assert audit_actions(db) == ["event.hidden"]


def test_unhide_restores_event_and_keeps_status(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    fake = make_event(db, "Fake concert", status="ACTIVE")
    client.post(f"/admin/events/{fake.id}/hide", json={"reason": "Wrong date"}, headers=auth_headers(adm))

    resp = client.post(f"/admin/events/{fake.id}/unhide", headers=auth_headers(adm))
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"
    assert fake.id in public_event_ids(client)
    assert audit_actions(db) == ["event.hidden", "event.unhidden"]


def test_summary_counts_moderation_queues(client, db):
    adm = make_user(db, "admin@example.com", status=UserStatus.admin)
    applicant = make_user(db, "org@example.com")
    make_user(db, "spam@example.com", is_active=False)
    make_event(db, "Fake concert", is_hidden=True)
    client.post("/auth/me/organizer-application", json=APPLICATION, headers=auth_headers(applicant))

    resp = client.get("/admin/summary", headers=auth_headers(adm))
    assert resp.json() == {"pending_applications": 1, "blocked_users": 1, "hidden_events": 1}


def test_hidden_and_cancelled_events_are_excluded_from_popular_and_favorites(client, db):
    fan = make_user(db, "fan@example.com")
    hidden = make_event(db, "Hidden", is_hidden=True)
    cancelled = make_event(db, "Cancelled", status="CANCELLED")
    visible = make_event(db, "Visible")
    for e in (hidden, cancelled, visible):
        db.add(UserFavoriteEvent(user_id=fan.id, event_id=e.id))
    db.commit()

    popular = client.get("/events/popular").json()["items"]
    assert [e["id"] for e in popular] == [visible.id]
    favorites = client.get("/events/me/favorites", headers=auth_headers(fan)).json()["items"]
    assert [e["id"] for e in favorites] == [visible.id]


def test_public_visibility_rule():
    from app.services.event_visibility import is_publicly_visible

    assert is_publicly_visible(Event(name="a", status="ACTIVE", is_hidden=False))
    assert not is_publicly_visible(Event(name="b", status="ACTIVE", is_hidden=True))
    assert not is_publicly_visible(Event(name="c", status="CANCELLED", is_hidden=False))
