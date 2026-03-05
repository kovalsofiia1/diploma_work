from typing import Optional, List
from pydantic import BaseModel, Field


class TicketBookRequest(BaseModel):
    event_id: int
    quantity: int = Field(default=1, ge=1, le=10)
    seat: Optional[str] = None


class TicketOut(BaseModel):
    id: int
    ticket_id: str
    code: str
    event_id: int
    user_id: int
    quantity: int
    seat: Optional[str] = None
    ticket_hash: str
    blockchain_tx_hash: Optional[str] = None
    status: str


class BookResponse(BaseModel):
    ticket: TicketOut


class VerifyResponse(BaseModel):
    status: str  # VALID | INVALID
    reason: Optional[str] = None
    ticket: Optional[TicketOut] = None


class MyTicketsOut(BaseModel):
    items: List[TicketOut]


