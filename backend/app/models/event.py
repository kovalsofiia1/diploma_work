from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class InternalEvent(Base):
    __tablename__ = "events_internal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uid: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)

    # Aligning with external fields for unified API
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    order_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    startDate: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    endDate: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    price_low: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price_high: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price_currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="internal", nullable=False)

    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ExternalEvent(Base):
    __tablename__ = "external_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uid: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    order_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    startDate: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    endDate: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    price_low: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price_high: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    price_currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="karabas.com", nullable=False)

    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

