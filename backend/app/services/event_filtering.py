"""Event filtering for the chatbot, written to be a drop-in for the filtering of `GET /events/all`.

`EventFilters` has the same fields, names and semantics as the query parameters of the endpoint
(`search`, `city`, `start_date`, `end_date`, `min_price`, `max_price`, `event_type`), and `search_events`
returns events in the same order, so the router can adopt this module later without changing what the
UI gets for clean data. It deliberately imports nothing from `app.routers`.

What it adds on top of the router logic (a superset, nothing the UI relies on is removed):
- prices are free text in the DB ("400 грн", "від 6200 грн", "безкоштовно"); `parse_price` reads them,
  the router's `int(price_low)` silently drops every such event as soon as a price bound is set;
- `event_type` knows the aliases of the scraped labels ("Концерти" ~ "MusicEvent", "Театр" ~
  "TheaterEvent", ...); any other text is a plain substring match, as in the router.

Router integration (NOT applied yet, the router is untouched), non-city branch of `unified_events`:

    filters = EventFilters(
        search=search, city=city, start_date=effective_start_date, end_date=end_date,
        min_price=min_price, max_price=max_price, event_type=event_type,
    )
    rows = search_events(db, filters)

For a city the stream branch can use the same call before its scraping steps. The only change the UI
would notice: events priced "400 грн" or "безкоштовно" stop disappearing from the price slider results.

Known router quirk kept on purpose: a date-only `end_date` ("2026-10-25", which is what the UI sends)
means midnight, so events later that day are excluded. Callers that want the whole day pass
`T23:59:59`, as the chatbot does.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.event import Event


@dataclass(frozen=True)
class EventFilters:
    """Same parameters as `GET /events/all`."""

    search: Optional[str] = None
    city: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    event_type: Optional[str] = None


def public_conditions() -> list:
    """SQL conditions every public listing must satisfy.

    The single place to add the "hidden by an admin" rule (P-02 / TD-02) so that the bot and, once it
    adopts this module, the router apply it together.
    """
    return [Event.status != "CANCELLED"]


# (words that identify the category in the user's text, patterns matched against the DB `type` column).
# Scraped types mix Ukrainian labels ("Концерти") and schema.org names ("MusicEvent").
EVENT_TYPE_GROUPS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("концерт", "music"), ("Концерт", "MusicEvent")),
    (("театр", "theater", "theatre"), ("Театр", "TheaterEvent")),
    (("стендап", "stand-up", "standup", "comedy", "комед"), ("Стендап", "ComedyEvent")),
    (("дітям", "дитяч", "kids"), ("Дітям",)),
    (("екскурс", "excursion"), ("Екскурс",)),
    (("семінар", "тренінг", "seminar", "training", "workshop", "воркшоп"), ("Семінар", "тренінг")),
    (("фестивал", "festival"), ("Фестивал",)),
)

_FREE_WORDS = ("безкошт", "безоплат", "безплат", "free", "вільн")
_FIRST_NUMBER = re.compile(r"\d[\d\s]*")


def expand_event_type(event_type: str) -> list[str]:
    """Patterns to match against `Event.event_type`: the whole alias group for a known category, else the text."""
    text = event_type.strip().casefold()
    for keys, patterns in EVENT_TYPE_GROUPS:
        if any(key in text for key in keys):
            return list(patterns)
    return [event_type.strip()]


def parse_price(text: Optional[str]) -> Optional[int]:
    """'400 грн' -> 400, '1 200 грн' -> 1200, 'від 6200 грн' -> 6200, '200-500 грн' -> 200, 'безкоштовно' -> 0, unknown -> None."""
    if text is None:
        return None
    value = str(text).strip()
    if not value:
        return None
    lowered = value.casefold()
    if any(word in lowered for word in _FREE_WORDS):
        return 0
    match = _FIRST_NUMBER.search(value)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group())
    return int(digits) if digits else None


def event_price(event: Event) -> Optional[int]:
    """Lowest known price of the event (`price_low`, falling back to `price_high`)."""
    price = parse_price(event.price_low)
    return price if price is not None else parse_price(event.price_high)


def matches_budget(event: Event, min_price: Optional[int], max_price: Optional[int]) -> bool:
    """No bound -> always True. With a bound an event of unknown price is excluded, as in the router."""
    if min_price is None and max_price is None:
        return True
    price = event_price(event)
    if price is None:
        return False
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    return True


def _apply_search(query, search: Optional[str]):
    term = (search or "").strip()
    if not term:
        return query
    pattern = f"%{term}%"
    return query.filter(
        or_(
            Event.name.ilike(pattern),
            Event.city.ilike(pattern),
            Event.location_name.ilike(pattern),
            Event.description.ilike(pattern),
            Event.event_type.ilike(pattern),
            Event.source_name.ilike(pattern),
        )
    )


def search_events(
    db: Session,
    filters: EventFilters,
    *,
    limit: Optional[int] = None,
    now: Optional[datetime] = None,
) -> list[Event]:
    """Public events from `start_date` (default: now) on, filtered, soonest first (router order)."""
    start_date = filters.start_date or now or datetime.utcnow()

    query = db.query(Event).filter(*public_conditions())
    query = _apply_search(query, filters.search)
    city = (filters.city or "").strip()
    if city:
        query = query.filter(Event.city.ilike(f"%{city}%"))
    query = query.filter(Event.startDate >= start_date)
    if filters.end_date:
        query = query.filter(Event.startDate <= filters.end_date)
    if filters.event_type and filters.event_type.strip():
        query = query.filter(or_(*[Event.event_type.ilike(f"%{p}%") for p in expand_event_type(filters.event_type)]))

    rows = query.order_by(Event.startDate.asc().nullslast(), Event.created_at.desc()).all()
    # Prices are free text, so the budget is checked in Python (also what the router does).
    rows = [e for e in rows if matches_budget(e, filters.min_price, filters.max_price)]
    return rows[:limit] if limit else rows
