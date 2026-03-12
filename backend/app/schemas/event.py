from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class EventBase(BaseModel):
    name: str
    type: Optional[str] = None
    url: Optional[str] = None
    order_url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    location_name: Optional[str] = None
    city: Optional[str] = None
    price_low: Optional[str] = None
    price_high: Optional[str] = None
    price_currency: Optional[str] = None
    image: Optional[str] = None
    source: Optional[str] = None
    verified: bool = True
    description: Optional[str] = None


class EventCreate(EventBase):
    name: str = Field(min_length=1)
    source: Optional[str] = "internal"


class EventUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    order_url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    location_name: Optional[str] = None
    city: Optional[str] = None
    price_low: Optional[str] = None
    price_high: Optional[str] = None
    price_currency: Optional[str] = None
    image: Optional[str] = None
    verified: Optional[bool] = None


class EventOut(EventBase):
    id: int
    uid: Optional[str] = None


class ExternalEventCreate(EventBase):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    source: Optional[str] = "karabas.com"


class EventKind(str, Enum):
    internal = "internal"
    external = "external"


class UnifiedEventOut(EventOut):
    kind: EventKind
    uid: str


class UnifiedEventsOut(BaseModel):
    items: List[UnifiedEventOut]


class ScrapeRequest(BaseModel):
    cities: List[str] = Field(min_length=1)
    sources: Optional[List[str]] = ["karabas.com", "concert.ua"]
    include_details: Optional[bool] = False
    max_events_per_city: Optional[int] = 30


