import asyncio
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.event import City
from app.schemas.chat import EventCategory
from app.services.chat_service import build_filters, sanitize_filters
from app.services.llm_client import LLMUnavailableError, get_llm_client

TODAY = date(2026, 10, 20)
NOW = datetime(2026, 10, 20, 12, 0)


# ---- sanitize_filters: model output is untrusted ----

def test_sanitize_keeps_valid_filters():
    filters = sanitize_filters(
        {
            "city": " Львів ",
            "date_from": "2026-10-24",
            "date_to": "2026-10-25",
            "min_price": 100,
            "max_price": "500",
            "event_type": "Concert",
        },
        TODAY,
    )

    assert filters.city == "Львів"
    assert filters.date_from == date(2026, 10, 24)
    assert filters.date_to == date(2026, 10, 25)
    assert (filters.min_price, filters.max_price) == (100, 500)
    assert filters.event_type == EventCategory.concert


def test_sanitize_drops_out_of_range_and_garbage_values():
    filters = sanitize_filters(
        {
            "city": 42,
            "date_from": "not a date",
            "date_to": "2099-01-01",
            "min_price": -5,
            "max_price": 10**9,
            "event_type": "rave'; DROP TABLE events;--",
        },
        TODAY,
    )

    assert filters.model_dump() == {
        "city": None,
        "date_from": None,
        "date_to": None,
        "min_price": None,
        "max_price": None,
        "event_type": None,
    }


def test_sanitize_fixes_reversed_ranges_and_past_dates():
    filters = sanitize_filters(
        {"date_from": "2026-10-01", "date_to": "2026-09-01", "min_price": 900, "max_price": 100},
        TODAY,
    )

    assert filters.date_from == TODAY  # past start is clamped to today
    assert filters.date_to is None  # end before start is dropped
    assert filters.min_price is None and filters.max_price == 100


def test_sanitize_caps_city_length():
    assert len(sanitize_filters({"city": "x" * 500}, TODAY).city) == 100


# ---- build_filters: city is resolved against the cities table ----

def test_build_filters_resolves_english_city_to_known_name(db_session, fake_llm):
    db_session.add(City(name="Львів", name_en="Lviv"))
    db_session.commit()
    llm = fake_llm({"city": "lviv"})

    filters = asyncio.run(build_filters(db_session, llm, "events in Lviv", NOW))

    assert filters.city == "Львів"


def test_build_filters_drops_unknown_city(db_session, fake_llm):
    llm = fake_llm({"city": "Atlantis"})

    filters = asyncio.run(build_filters(db_session, llm, "events in Atlantis", NOW))

    assert filters.city is None


def test_build_filters_sends_today_and_user_text_to_model(db_session, fake_llm):
    llm = fake_llm({})

    asyncio.run(build_filters(db_session, llm, "що робити завтра?", NOW))

    system, user = llm.calls[0]
    assert "2026-10-20" in system
    assert user == "що робити завтра?"


# ---- POST /chat/messages ----

@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    # No `with`: skips the lifespan (scheduler, scraping) so the test stays offline.
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_chat_endpoint_returns_validated_filters(client, fake_llm):
    llm = fake_llm({"city": None, "max_price": 300, "event_type": "standup"})
    app.dependency_overrides[get_llm_client] = lambda: llm

    response = client.post("/chat/messages", json={"message": "стендап до 300 грн"})

    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["max_price"] == 300
    assert body["filters"]["event_type"] == "standup"
    assert body["events"] == []


def test_chat_endpoint_is_public(client, fake_llm):
    app.dependency_overrides[get_llm_client] = lambda: fake_llm({})

    response = client.post("/chat/messages", json={"message": "hi"})  # no Authorization header

    assert response.status_code == 200


def test_chat_endpoint_returns_503_when_llm_is_down(client, fake_llm):
    app.dependency_overrides[get_llm_client] = lambda: fake_llm(LLMUnavailableError("boom"))

    response = client.post("/chat/messages", json={"message": "концерти"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "llm_unavailable"


def test_regular_endpoints_keep_working_when_llm_is_down(client, fake_llm):
    app.dependency_overrides[get_llm_client] = lambda: fake_llm(LLMUnavailableError("boom"))
    client.post("/chat/messages", json={"message": "концерти"})

    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("payload", [{"message": ""}, {"message": "x" * 501}, {}])
def test_chat_endpoint_rejects_invalid_request(client, payload):
    assert client.post("/chat/messages", json=payload).status_code == 422
