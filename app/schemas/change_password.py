import re
from pydantic import BaseModel, Field, field_validator


class AdminChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Current password is required.")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not v:
            raise ValueError("New password is required.")
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("New password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("New password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("New password must contain at least one number.")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", v):
            raise ValueError("New password must contain at least one special character (!@#$%^&*...).")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, values) -> str:
        new_pwd = values.data.get("new_password")
        if new_pwd and v != new_pwd:
            raise ValueError("Confirm password must exactly match the new password.")
        return v
