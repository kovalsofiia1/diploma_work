from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from enum import Enum
from datetime import date


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

