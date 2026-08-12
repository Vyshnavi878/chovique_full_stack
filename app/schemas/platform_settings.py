"""Pydantic schemas for Superadmin Platform Settings."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas (one per settings tab)
# ──────────────────────────────────────────────────────────────────────────────

class StoreConfigSchema(BaseModel):
    store_front_name: str = Field(..., min_length=2, max_length=200)
    support_email: EmailStr
    support_phone: str = Field(..., min_length=7, max_length=30)
    store_address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(default="", max_length=20)
    base_currency: str = Field(..., min_length=2, max_length=10)
    timezone: str = Field(..., min_length=3, max_length=60)
    business_status: str = Field(..., pattern="^(active|paused|closed)$")

    @field_validator("support_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)\+]", "", v)
        if not re.match(r"^\d{7,15}$", cleaned):
            raise ValueError("Enter a valid phone number (7–15 digits).")
        return v

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        if v and not re.match(r"^\d{4,10}$", v.strip()):
            raise ValueError("Pincode must contain 4–10 digits.")
        return v


class PaymentShippingSchema(BaseModel):
    cod_enabled: bool = True
    gst_rate: float = Field(..., ge=0.0, le=100.0)
    platform_fee: float = Field(..., ge=0.0)
    standard_shipping_charge: float = Field(..., ge=0.0)
    free_shipping_min_order: float = Field(..., ge=0.0)
    maximum_cod_order_value: float = Field(..., ge=0.0)


class CustomerOrderSchema(BaseModel):
    customer_registration_enabled: bool = True
    guest_checkout_enabled: bool = True
    minimum_order_value: float = Field(..., ge=0.0)
    order_cancellation_enabled: bool = True
    cancellation_time_limit: int = Field(..., ge=1)
    return_refund_enabled: bool = True


class SystemSecuritySchema(BaseModel):
    maintenance_mode: bool = False
    admin_session_timeout: int = Field(..., ge=5, le=1440)
    max_login_attempts: int = Field(..., ge=1, le=20)
    account_lockout_duration: int = Field(..., ge=1, le=1440)
    require_admin_password_change: bool = False


# ──────────────────────────────────────────────────────────────────────────────
# Full settings schema (GET response + PUT request)
# ──────────────────────────────────────────────────────────────────────────────

class PlatformSettingsResponse(BaseModel):
    id: str

    # Store Config
    store_front_name: str
    support_email: str
    support_phone: str
    store_address: str
    city: str
    state: str
    country: str
    pincode: str
    base_currency: str
    timezone: str
    business_status: str

    # Payment & Shipping
    cod_enabled: bool
    gst_rate: float
    platform_fee: float
    standard_shipping_charge: float
    free_shipping_min_order: float
    maximum_cod_order_value: float

    # Customer & Order
    customer_registration_enabled: bool
    guest_checkout_enabled: bool
    minimum_order_value: float
    order_cancellation_enabled: bool
    cancellation_time_limit: int
    return_refund_enabled: bool

    # System & Security
    maintenance_mode: bool
    admin_session_timeout: int
    max_login_attempts: int
    account_lockout_duration: int
    require_admin_password_change: bool

    updated_at: datetime
    updated_by: Optional[str] = None

    model_config = {"from_attributes": True}


class PlatformSettingsUpdateRequest(
    StoreConfigSchema,
    PaymentShippingSchema,
    CustomerOrderSchema,
    SystemSecuritySchema,
):
    """Full update payload — all tabs merged."""
    pass


class MaintenanceModeRequest(BaseModel):
    enable: bool
    confirmed: bool = Field(
        ...,
        description="Must be True to confirm the maintenance mode toggle."
    )

    @field_validator("confirmed")
    @classmethod
    def must_confirm(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Confirmation is required to toggle maintenance mode.")
        return v


class MaintenanceModeResponse(BaseModel):
    maintenance_mode: bool
    message: str
