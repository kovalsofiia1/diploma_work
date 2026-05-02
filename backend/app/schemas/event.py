from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


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
    additional: Optional[str] = None
    total_places: Optional[int] = Field(default=None, ge=1)
    booked_places: Optional[int] = Field(default=None, ge=0)
    available_places: Optional[int] = Field(default=None, ge=0)


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
    additional: Optional[str] = None
    total_places: Optional[int] = Field(default=None, ge=1)


class EventOut(EventBase):
    id: int
    uid: Optional[str] = None
    isSaved: bool = False
    can_edit: bool = False
    organizer_name: Optional[str] = None
    organizer_email: Optional[str] = None
    organizer_phone: Optional[str] = None
    organizer_description: Optional[str] = None
    organizer_organization_name: Optional[str] = None


class EventUserRole(str, Enum):
    organizer = "organizer"
    scanner = "scanner"


class EventMembersUpsertRequest(BaseModel):
    emails: List[EmailStr] = Field(min_length=1)
    role: EventUserRole = EventUserRole.scanner


class EventMembersUpsertResponse(BaseModel):
    role: EventUserRole
    added: List[str] = []
    updated: List[str] = []
    missing: List[str] = []


class EventMemberOut(BaseModel):
    user_id: int
    email: str
    full_name: Optional[str] = None
    role: EventUserRole


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
    total: Optional[int] = None


class ScrapeRequest(BaseModel):
    cities: List[str] = Field(min_length=1)
    sources: Optional[List[str]] = ["karabas.com", "concert.ua"]
    include_details: Optional[bool] = False
    max_events_per_city: Optional[int] = 30


