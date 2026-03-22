from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Date, Text, Enum as SAEnum, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuthProvider(str, Enum):
    local = "local"
    google = "google"


class UserStatus(str, Enum):
    admin = "admin"
    verified_user = "verified user"
    user = "user"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    provider: Mapped[AuthProvider] = mapped_column(SAEnum(AuthProvider), default=AuthProvider.local, nullable=False)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.user, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserCity(Base):
    __tablename__ = "user_cities"
    __table_args__ = (UniqueConstraint("user_id", "city", name="uq_user_city"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserFavoriteEvent(Base):
    __tablename__ = "user_favorite_events"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_user_favorite_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

