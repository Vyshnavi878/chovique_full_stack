from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ==========================================================
# Base User Schema
# ==========================================================

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None

    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None


# ==========================================================
# Update Profile
# ==========================================================

class UserUpdate(UserBase):
    pass


# ==========================================================
# User Response
# ==========================================================

class UserResponse(UserBase):
    id: str

    role: str

    is_email_verified: bool
    is_active: bool

    last_login_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)