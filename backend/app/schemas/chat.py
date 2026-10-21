from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SearchFilters(BaseModel):
    """The query parameters of GET /events/all, filled in by the model from the user's question."""

    search: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_price: Optional[int] = Field(default=None, ge=0, le=100_000)
    max_price: Optional[int] = Field(default=None, ge=0, le=100_000)
    event_type: Optional[str] = Field(default=None, max_length=64)

    @field_validator("search", "city", "event_type", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def check_ranges(self):
        # "Filters within allowed bounds": a reversed range is a bad answer from the model, not a query.
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date is before start_date")
        if self.min_price is not None and self.max_price is not None and self.max_price < self.min_price:
            raise ValueError("max_price is below min_price")
        return self


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
    status: str  # "found" | "not_found" | "not_understood"
    reply: str
    events: List[ChatEventOut] = Field(default_factory=list, max_length=5)
    suggestions: List[str] = Field(default_factory=list)
    filters: SearchFilters
    degraded: bool = False
