from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Enum as SAEnum, UniqueConstraint
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

    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    provider: Mapped[AuthProvider] = mapped_column(SAEnum(AuthProvider), default=AuthProvider.local, nullable=False)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.user, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

