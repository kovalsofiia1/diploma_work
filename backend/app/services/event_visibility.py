"""The single rule for which events the public may see.

Every public listing (catalog, search, city stream, popular events, favorites,
the digest email and the chatbot search) must go through ``publicly_visible``.
A new endpoint that filters events by hand risks showing events an admin hid.
"""

from sqlalchemy import and_
from sqlalchemy.sql.elements import ColumnElement

from app.models.event import Event

CANCELLED = "CANCELLED"


def public_events_clause() -> ColumnElement[bool]:
    return and_(Event.status != CANCELLED, Event.is_hidden.is_(False))


def publicly_visible(query):
    """Narrow an Event query to events the public may see."""
    return query.filter(public_events_clause())


def is_publicly_visible(event: Event) -> bool:
    return event.status != CANCELLED and not event.is_hidden
