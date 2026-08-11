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
        digits = re.sub(r"\D", "", v)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Please enter a valid phone number (7-15 digits).")
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
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
