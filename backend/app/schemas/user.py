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


class UserCitiesRequest(BaseModel):
    cities: List[str]


class UserCitiesResponse(BaseModel):
    cities: List[str]


class UserProfileStatsOut(BaseModel):
    created_events: int = 0
    visited_events: int = 0
    purchased_tickets: int = 0

