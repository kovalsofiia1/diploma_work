import asyncio
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.schemas.chat import SearchFilters
from app.services.chat_service import _calendar, build_filters
from app.services.llm_client import LLMBadOutputError, LLMUnavailableError, get_llm_client

NOW = datetime(2026, 10, 20, 12, 0)


# ---- filters: same parameters as GET /events/all, validated ----

def test_filters_accept_the_events_all_parameters():
    filters = SearchFilters.model_validate(
        {
            "city": " Львів ",
            "start_date": "2026-10-24T00:00:00",
            "end_date": "2026-10-25T23:59:59",
            "min_price": 100,
            "max_price": "500",
            "event_type": "Концерти",
            "search": "",
        }
    )

    assert filters.city == "Львів"
    assert filters.start_date == datetime(2026, 10, 24)
    assert filters.end_date == datetime(2026, 10, 25, 23, 59, 59)
    assert (filters.min_price, filters.max_price) == (100, 500)
    assert filters.search is None  # blank means "not set"


@pytest.mark.parametrize(
    "raw",
    [
        {"max_price": -5},
        {"max_price": 10**9},
        {"min_price": 900, "max_price": 100},
        {"start_date": "2026-10-25T00:00:00", "end_date": "2026-10-24T00:00:00"},
        {"start_date": "not a date"},
        {"city": "x" * 500},
    ],
)
def test_filters_outside_allowed_bounds_are_rejected(raw):
    with pytest.raises(Exception):
        SearchFilters.model_validate(raw)


def test_build_filters_turns_invalid_model_output_into_bad_output_error(fake_llm):
    llm = fake_llm({"max_price": -5})

    with pytest.raises(LLMBadOutputError):
        asyncio.run(build_filters(llm, "щось дешеве", NOW))


def test_build_filters_sends_calendar_and_user_text_to_model(fake_llm):
    llm = fake_llm({})

    asyncio.run(build_filters(llm, "що робити завтра?", NOW))

    system, user = llm.calls[0]
    assert "tomorrow=2026-10-21" in system
    assert "this weekend=2026-10-24..2026-10-25" in system
    assert user == "що робити завтра?"


def test_calendar_resolves_weekend_and_next_week():
    from datetime import date

    tuesday = _calendar(date(2026, 10, 20))
    assert tuesday["tomorrow"] == "2026-10-21"
    assert (tuesday["weekend_start"], tuesday["weekend_end"]) == ("2026-10-24", "2026-10-25")
    assert (tuesday["next_week_start"], tuesday["next_week_end"]) == ("2026-10-26", "2026-11-01")

    saturday = _calendar(date(2026, 10, 24))
    assert (saturday["weekend_start"], saturday["weekend_end"]) == ("2026-10-24", "2026-10-25")


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


def test_chat_endpoint_returns_the_filters_it_searched_with(client, fake_llm):
    llm = fake_llm({"max_price": 300, "event_type": "Стендап"})
    app.dependency_overrides[get_llm_client] = lambda: llm

    response = client.post("/chat/messages", json={"message": "стендап до 300 грн"})

    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["max_price"] == 300
    assert body["filters"]["event_type"] == "Стендап"
    assert body["status"] == "not_found"  # empty test DB
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
