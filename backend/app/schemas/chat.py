from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """Closed set of categories the model may pick; mapped to DB `type` values in event_search."""

    concert = "concert"
    theater = "theater"
    standup = "standup"
    kids = "kids"
    excursion = "excursion"
    seminar = "seminar"
    festival = "festival"
    it = "it"


class SearchFilters(BaseModel):
    """Validated search parameters built from the user's question."""

    city: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_price: Optional[int] = Field(default=None, ge=0)
    max_price: Optional[int] = Field(default=None, ge=0)
    event_type: Optional[EventCategory] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ChatEventOut(BaseModel):
    id: int
    uid: str
    name: str
    type: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    city: Optional[str] = None
    location_name: Optional[str] = None
    price_low: Optional[str] = None
    price_high: Optional[str] = None
    price_currency: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    order_url: Optional[str] = None
    source: Optional[str] = None


class ChatResponse(BaseModel):
    status: str  # "found" | "not_found"
    reply: str
    events: List[ChatEventOut] = Field(default_factory=list, max_length=5)
    suggestions: List[str] = Field(default_factory=list)
    filters: SearchFilters
    degraded: bool = False
