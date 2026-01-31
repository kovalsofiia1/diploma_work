from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum


class UserStatus(str, Enum):
    admin = "admin"
    verified_user = "verified user"
    user = "user"


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool
    status: UserStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleAuthStartResponse(BaseModel):
    authorization_url: str

