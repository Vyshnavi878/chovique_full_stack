from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


class AdminProfileUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, description="Full Name (minimum 2 characters)")
    email: EmailStr = Field(..., description="Valid Email address")
    phone: str = Field(..., description="Valid Phone Number")
    address: str = Field(..., min_length=10, description="Address (minimum 10 characters)")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full Name must be at least 2 characters.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Phone number is required.")
        if not re.match(r"^[6-9][0-9]{9}$", v):
            raise ValueError("Enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.")
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Address must be at least 10 characters.")
        return v


class AdminProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = ""
    address: Optional[str] = ""
    role: str
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
