from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserStatus(str, Enum):
    admin = "admin"
    verified_user = "verified user"
    user = "user"


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)
    verification_code: str = Field(min_length=4, max_length=12)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    status: UserStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleAuthStartResponse(BaseModel):
    authorization_url: str


class RegisterVerificationSendRequest(BaseModel):
    email: EmailStr


class RegisterVerificationSendResponse(BaseModel):
    message: str


class PasswordResetSendCodeRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8)


class PasswordResetResponse(BaseModel):
    message: str


class SmtpEmailSendRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(min_length=1, max_length=255)
    html: str = Field(min_length=1)
    plain_text: Optional[str] = None


class SmtpEmailSendResponse(BaseModel):
    message: str


class UserCitiesRequest(BaseModel):
    cities: List[str]


class UserCitiesResponse(BaseModel):
    cities: List[str]


class UserProfileStatsOut(BaseModel):
    created_events: int = 0
    visited_events: int = 0
    purchased_tickets: int = 0


class OrganizerApplicationStatus(str, Enum):
    not_requested = "not_requested"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OrganizerApplicationSubmitRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    contact_phone: str = Field(min_length=6, max_length=64)
    motivation: str = Field(min_length=20, max_length=2000)
    experience: Optional[str] = Field(default=None, max_length=2000)


class OrganizerApplicationOut(BaseModel):
    status: OrganizerApplicationStatus
    can_create_events: bool
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class OrganizerApplicationAdminOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    user_full_name: Optional[str] = None
    organization_name: str
    contact_phone: str
    motivation: str
    experience: Optional[str] = None
    status: OrganizerApplicationStatus
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class OrganizerApplicationRejectRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=500)


class OrganizerProfileUpdateRequest(BaseModel):
    organization_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    contact_phone: Optional[str] = Field(default=None, min_length=6, max_length=64)
    motivation: Optional[str] = Field(default=None, min_length=20, max_length=2000)
    experience: Optional[str] = Field(default=None, max_length=2000)


class OrganizerProfileOut(BaseModel):
    organization_name: str
    contact_phone: str
    motivation: str
    experience: Optional[str] = None

