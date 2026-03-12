from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


SourceName = Literal["karabas.com", "concert.ua", "dou.ua"]

class ScrapeEventsRequest(BaseModel):
    cities: list[str] = Field(min_length=1, description="City names or slugs.")

    sources: list[SourceName] = Field(
        default_factory=lambda: ["karabas.com", "concert.ua", "dou.ua"],
        description="Which sources to scrape.",
    )

    include_details: bool = Field(
        default=False,
        description="If true, for concert.ua additionally fetch each event detail page to enrich fields (slower).",
    )

    max_events_per_city: int = Field(
        default=30,
        ge=1,
        le=200,
        description="Limit events per city per source (for safety).",
    )

    batch_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Batch size for chunked responses (and streaming).",
    )

    concurrency: int = Field(
        default=6,
        ge=1,
        le=50,
        description="Max concurrent city tasks.",
    )

    request_timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)


class NormalizedEvent(BaseModel):
    # Align to backend `EventOut` as closely as possible
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
    source: SourceName

    # Extra fields are allowed (backend will ignore if it doesn't use them yet)
    description: Optional[str] = None


class ScrapeBatch(BaseModel):
    batch_index: int
    items: list[NormalizedEvent]
    done: bool = False


class ScrapeEventsResponse(BaseModel):
    items: list[NormalizedEvent]
    batches: list[ScrapeBatch]
    meta: dict


