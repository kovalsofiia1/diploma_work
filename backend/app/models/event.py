from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)


class CityScrapeState(Base):
    __tablename__ = "city_scrape_state"

    city_key: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)
    city_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    is_scraping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class CityActivityType(str, Enum):
    search = "search"
    subscription = "subscription"


class CityActivityLog(Base):
    __tablename__ = "city_activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    activity_type: Mapped[CityActivityType] = mapped_column(
        SAEnum(CityActivityType, native_enum=False),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("source_name", "source_event_id", name="uq_events_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uid: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)

    # Attribute names preserved; mapped to existing column names in DB
    name: Mapped[str] = mapped_column("title", String(255), nullable=False, index=True)
    startDate: Mapped[Optional[datetime]] = mapped_column("start_datetime", DateTime, nullable=True, index=True)
    endDate: Mapped[Optional[datetime]] = mapped_column("end_datetime", DateTime, nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column("location", String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Source metadata per EVENTS_README
    source_type: Mapped[str] = mapped_column(String(16), default="INTERNAL", nullable=False)  # INTERNAL | EXTERNAL
    source_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Extra fields for parsed data
    price_low: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price_high: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price_currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column("type", String(128), nullable=True)
    order_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_places: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)  # ACTIVE | CANCELLED | DRAFT
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EventUserRole(str, Enum):
    organizer = "organizer"
    scanner = "scanner"


class EventUser(Base):
    __tablename__ = "event_users"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_users_event_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[EventUserRole] = mapped_column(SAEnum(EventUserRole, native_enum=False), default=EventUserRole.scanner, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
