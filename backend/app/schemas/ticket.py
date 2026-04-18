from typing import Optional, List
from pydantic import BaseModel, Field


class TicketBookRequest(BaseModel):
    event_id: int
    quantity: int = Field(default=1, ge=1, le=10)
    seat: Optional[str] = None


class TicketBookBatchRequest(BaseModel):
    event_id: int
    attendee_names: List[str] = Field(min_length=1, max_length=10)


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
    ticket_hash: str
    blockchain_tx_hash: Optional[str] = None
    status: str
    used: bool = False
    created_at: Optional[str] = None


class BookResponse(BaseModel):
    ticket: TicketOut


class BookBatchResponse(BaseModel):
    tickets: List[TicketOut]


class VerifyResponse(BaseModel):
    status: str  # VALID | INVALID
    reason: Optional[str] = None
    ticket: Optional[TicketOut] = None


class MyTicketsOut(BaseModel):
    items: List[TicketOut]


