import asyncio
from datetime import datetime, timedelta

import pytest

from app.models.event import Event
from app.services.event_filtering import (
    EventFilters,
    expand_event_type,
    matches_budget,
    parse_price,
    search_events,
)

NOW = datetime.utcnow()


def make_event(db, name, *, city="Львів", days=1, status="ACTIVE", price="200", price_high=None, type_="Концерти", **extra):
    event = Event(
        name=name,
        city=city,
        startDate=NOW + timedelta(days=days),
        status=status,
        price_low=price,
        price_high=price_high,
        event_type=type_,
        source_type="EXTERNAL",
        source_name="karabas.com",
        **extra,
    )
    db.add(event)
    db.commit()
    return event


def iso(days: int, end_of_day: bool = False) -> str:
    return (NOW + timedelta(days=days)).strftime("%Y-%m-%dT23:59:59" if end_of_day else "%Y-%m-%dT00:00:00")


def names(events):
    return [e.name for e in events]


# ---- parity with the router: the same parameters give the same events in the same order ----

def router_ids(db, **params):
    """What GET /events/all (non-city path) returns for these parameters."""
    from app.routers.events import unified_events

    args = dict(search=None, city=None, start_date=None, end_date=None, min_price=None, max_price=None, event_type=None)
    args.update(params)
    response = asyncio.run(unified_events(skip=0, limit=100, db=db, request=None, **args))
    return [item.id for item in response.items]


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"max_price": 500},
        {"min_price": 300, "max_price": 900},
        {"min_price": 300},
        {"event_type": "Концерти"},
        {"event_type": "Театр"},
        {"search": "show"},
        {"end_date": datetime.utcnow() + timedelta(days=3)},
        {"start_date": datetime.utcnow() + timedelta(days=2)},
        {"max_price": 500, "end_date": datetime.utcnow() + timedelta(days=4), "event_type": "Концерти"},
    ],
)
def test_same_events_in_same_order_as_the_router_on_clean_data(db_session, params):
    make_event(db_session, "Early show", price="100", days=1)
    make_event(db_session, "Mid show", price="400", days=2, type_="Театр")
    make_event(db_session, "Late show", price="900", days=5)
    make_event(db_session, "Kyiv show", price="300", days=3, city="Київ")
    make_event(db_session, "Cancelled show", price="300", days=2, status="CANCELLED")
    make_event(db_session, "Past show", price="300", days=-4)
    make_event(db_session, "Plain thing", price="50", days=4)

    ours = [e.id for e in search_events(db_session, EventFilters(**params))]

    assert ours == router_ids(db_session, **params)


def router_ids_for_city(db, city, **params):
    """What GET /events/all returns for a city: the first chunk of its stream (DB snapshot, before any scraping)."""
    import json

    from app.routers.events import unified_events

    args = dict(search=None, start_date=None, end_date=None, min_price=None, max_price=None, event_type=None)
    args.update(params)

    async def first_chunk():
        response = await unified_events(city=city, skip=0, limit=100, db=db, request=None, **args)
        stream = response.body_iterator
        try:
            return json.loads(await stream.__anext__())
        finally:
            await stream.aclose()

    return [item["id"] for item in asyncio.run(first_chunk())["items"]]


@pytest.mark.parametrize("params", [{}, {"max_price": 500}, {"event_type": "Театр"}, {"search": "show"}])
def test_same_as_the_router_for_a_city(db_session, params):
    make_event(db_session, "A show", price="300", days=2)
    make_event(db_session, "B show", price="900", days=1, type_="Театр")
    make_event(db_session, "C show", price="100", days=3, city="Київ")
    make_event(db_session, "D thing", price="200", days=4)
    make_event(db_session, "E show", price="200", days=5, status="CANCELLED")

    ours = [e.id for e in search_events(db_session, EventFilters(city="Львів", **params))]

    assert ours == router_ids_for_city(db_session, "Львів", **params)


# ---- what the router cannot do ----

def test_text_prices_are_read_by_the_budget_filter(db_session):
    cheap = make_event(db_session, "Cheap", price="400 грн", days=1)
    free = make_event(db_session, "Free", price="безкоштовно", days=2)
    make_event(db_session, "Pricey", price="1 200 грн", days=3)
    make_event(db_session, "From", price="від 6200 грн", days=4)
    make_event(db_session, "Unknown", price=None, days=5)

    found = search_events(db_session, EventFilters(max_price=500))

    assert names(found) == ["Cheap", "Free"]
    assert {cheap.id, free.id} == {e.id for e in found}


def test_router_drops_text_prices_so_the_service_is_a_strict_superset(db_session):
    make_event(db_session, "Numeric", price="300", days=1)
    make_event(db_session, "Text", price="300 грн", days=2)

    assert len(router_ids(db_session, max_price=500)) == 1
    assert names(search_events(db_session, EventFilters(max_price=500))) == ["Numeric", "Text"]


def test_min_price_uses_the_lowest_known_price_with_high_as_fallback(db_session):
    make_event(db_session, "Only high", price=None, price_high="700 грн", days=1)
    make_event(db_session, "Low", price="100", days=2)

    assert names(search_events(db_session, EventFilters(min_price=500))) == ["Only high"]


@pytest.mark.parametrize("label", ["Концерти", "MusicEvent"])
def test_event_type_alias_returns_both_spellings(db_session, label):
    make_event(db_session, "Ukrainian", type_="Концерти", days=1)
    make_event(db_session, "Schema", type_="MusicEvent", days=2)
    make_event(db_session, "Other", type_="Театр", days=3)

    assert names(search_events(db_session, EventFilters(event_type=label))) == ["Ukrainian", "Schema"]


def test_unknown_event_type_is_a_plain_substring_like_in_the_router(db_session):
    make_event(db_session, "Tagged", type_="Концерт, Рок", days=1)
    make_event(db_session, "Other", type_="Театр", days=2)

    assert names(search_events(db_session, EventFilters(event_type="Рок"))) == ["Tagged"]


def test_limit_cancelled_and_past_events(db_session):
    for i in range(6):
        make_event(db_session, f"Show {i}", days=i + 1)
    make_event(db_session, "Cancelled", status="CANCELLED", days=1)
    make_event(db_session, "Past", days=-2)

    found = search_events(db_session, EventFilters(), limit=5)

    assert len(found) == 5
    assert "Cancelled" not in names(found) and "Past" not in names(found)
    assert names(found) == [f"Show {i}" for i in range(5)]


def test_end_of_day_end_date_includes_the_whole_day(db_session):
    evening = make_event(db_session, "Evening", days=2)
    evening.startDate = (NOW + timedelta(days=2)).replace(hour=21, minute=0)
    db_session.commit()
    end_day = (NOW + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)

    assert search_events(db_session, EventFilters(end_date=end_day)) == []  # router quirk: date-only = midnight
    assert names(search_events(db_session, EventFilters(end_date=end_day.replace(hour=23, minute=59, second=59)))) == ["Evening"]


# ---- helpers ----

@pytest.mark.parametrize(
    "text, expected",
    [
        ("400 грн", 400),
        ("400", 400),
        ("1 200 грн", 1200),
        ("від 6200 грн", 6200),
        ("200-500 грн", 200),
        ("Безкоштовно", 0),
        ("безкоштовно", 0),
        ("Безоплатно", 0),
        ("Безплатно", 0),
        ("вільний вхід", 0),
        ("", None),
        (None, None),
        ("уточнюйте", None),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_matches_budget_without_bounds_keeps_unknown_prices():
    assert matches_budget(Event(name="x", price_low=None), None, None)
    assert not matches_budget(Event(name="x", price_low=None), None, 100)


def test_expand_event_type():
    assert expand_event_type("Концерти") == ["Концерт", "MusicEvent"]
    assert expand_event_type("comedy") == ["Стендап", "ComedyEvent"]
    assert expand_event_type("Рок") == ["Рок"]
