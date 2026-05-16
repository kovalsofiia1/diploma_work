from app.models.event import Event
from app.models.user import AuthProvider, User
from app.services.qr_service import generate_ticket_qr_token
from app.services.ticket_service import book_ticket, checkin_ticket, verify_ticket_qr


def _create_user_and_event(db_session) -> tuple[User, Event]:
    user = User(
        email="buyer@example.com",
        full_name="Ticket Buyer",
        hashed_password="hashed",
        provider=AuthProvider.local,
    )
    event = Event(
        uid="internal-event-1",
        name="Test Event",
        source_type="INTERNAL",
        status="ACTIVE",
        city="Kyiv",
    )
    db_session.add_all([user, event])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(event)
    return user, event


def test_book_ticket_creates_ticket_and_qr_payload(db_session):
    user, event = _create_user_and_event(db_session)

    ticket, qr = book_ticket(
        db_session,
        event_id=event.id,
        user_id=user.id,
        quantity=2,
        seat="Row 1 Seat 1",
        seat_id="A1",
        attendee_name="Ticket Buyer",
        price_amount=500,
        price_currency="UAH",
    )

    assert ticket.id is not None
    assert ticket.token_id == ticket.id
    assert ticket.event_id == event.id
    assert ticket.user_id == user.id
    assert ticket.quantity == 2
    assert ticket.seat_id == "A1"
    assert ticket.status == "pending_onchain"
    assert ticket.used is False
    assert ticket.ticket_hash.startswith("0x")
    assert len(ticket.ticket_hash) == 66
    assert qr["ticket_id"] == ticket.ticket_id
    assert "qr_token" in qr


def test_verify_ticket_qr_accepts_active_ticket(db_session):
    user, event = _create_user_and_event(db_session)
    ticket, qr = book_ticket(db_session, event_id=event.id, user_id=user.id)

    ok, reason, verified_ticket = verify_ticket_qr(db_session, qr_token=qr["qr_token"])

    assert ok is True
    assert reason is None
    assert verified_ticket.id == ticket.id


def test_verify_ticket_qr_rejects_used_ticket(db_session):
    user, event = _create_user_and_event(db_session)
    ticket, qr = book_ticket(db_session, event_id=event.id, user_id=user.id)
    ticket.used = True
    db_session.add(ticket)
    db_session.commit()

    ok, reason, verified_ticket = verify_ticket_qr(db_session, qr_token=qr["qr_token"])

    assert ok is False
    assert reason == "Already used"
    assert verified_ticket.id == ticket.id


def test_verify_ticket_qr_rejects_unknown_ticket(db_session):
    _user, event = _create_user_and_event(db_session)
    qr_token = generate_ticket_qr_token(ticket_id=999, event_id=event.id)

    ok, reason, ticket = verify_ticket_qr(db_session, qr_token=qr_token)

    assert ok is False
    assert reason == "Ticket not found"
    assert ticket is None


def test_checkin_ticket_marks_ticket_as_used(db_session):
    user, event = _create_user_and_event(db_session)
    ticket, qr = book_ticket(db_session, event_id=event.id, user_id=user.id)

    ok, reason, checked_ticket = checkin_ticket(
        db_session,
        qr_token=qr["qr_token"],
        staff_user_id=user.id,
    )

    assert ok is True
    assert reason is None
    assert checked_ticket.id == ticket.id
    assert checked_ticket.used is True
    assert checked_ticket.status == "used"
