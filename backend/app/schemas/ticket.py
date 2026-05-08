from typing import Optional, List
from pydantic import BaseModel, Field


class TicketBookRequest(BaseModel):
    event_id: int
    quantity: int = Field(default=1, ge=1, le=10)
    seat: Optional[str] = None


class TicketBookBatchItem(BaseModel):
    attendee_name: str = Field(min_length=1, max_length=255)
    seat_id: Optional[str] = Field(default=None, max_length=64)
    seat_label: Optional[str] = Field(default=None, max_length=64)


class TicketBookBatchRequest(BaseModel):
    event_id: int
    attendee_names: List[str] = Field(default_factory=list, max_length=10)
    items: Optional[List[TicketBookBatchItem]] = Field(default=None, max_length=10)


class TicketBookSeatBatchRequest(BaseModel):
    event_id: int
    items: List[TicketBookBatchItem] = Field(min_length=1, max_length=10)


class TicketOut(BaseModel):
    id: int
    ticket_id: str
    code: str
    event_id: int
    event_name: Optional[str] = None
    event_start_date: Optional[str] = None
    event_location: Optional[str] = None
    event_city: Optional[str] = None
    user_id: int
    quantity: int
    seat: Optional[str] = None
    seat_id: Optional[str] = None
    attendee_name: Optional[str] = None
    price_amount: Optional[int] = None
    price_currency: Optional[str] = None
    ticket_hash: str
    blockchain_tx_hash: Optional[str] = None
    status: str
    used: bool = False
    created_at: Optional[str] = None
    qr_token: Optional[str] = None


class BookResponse(BaseModel):
    ticket: TicketOut


class BookBatchResponse(BaseModel):
    tickets: List[TicketOut]


class VerifyResponse(BaseModel):
    status: str  # VALID | INVALID
    reason: Optional[str] = None
    ticket: Optional[TicketOut] = None


class VerifyRequest(BaseModel):
    qr_token: str


class MyTicketsOut(BaseModel):
    items: List[TicketOut]


class OccupiedSeatsOut(BaseModel):
    seat_ids: List[str]


