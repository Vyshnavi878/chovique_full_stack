from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime

class CouponValidationRequest(BaseModel):
    code: str


class CouponValidationResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str = "PERCENTAGE"
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    calculated_discount: float = 0.0
    message: str


class UserCouponResponse(BaseModel):
    id: Optional[str] = None
    code: str
    name: Optional[str] = None
    description: str = ""
    coupon_type: str = "CUSTOMER"
    discount_type: str = "PERCENTAGE"
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    maximum_discount_amount: float = 0.0
    minimum_order_amount: float = 0.0
    start_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    status: str = "ACTIVE"

    model_config = ConfigDict(from_attributes=True)


class CouponCreate(BaseModel):
    code: str
    name: Optional[str] = None
    description: str = ""
    coupon_type: str = "CUSTOMER" # CUSTOMER or INFLUENCER
    discount_type: str = "PERCENTAGE"
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    maximum_discount_amount: float = 0.0
    minimum_order_amount: float = 0.0
    start_at: Optional[str] = None
    expires_at: Optional[str] = None
    usage_limit: int = 0
    per_user_usage_limit: int = 1
    is_active: bool = True

    eligibility_rule: str = "ALL_USERS"
    eligibility_value: Optional[str] = None

    applicability: str = "ENTIRE_STORE"
    applicable_ids: List[str] = []

    model_config = ConfigDict(extra="allow")

    @field_validator("start_at", "expires_at", mode="before")
    @classmethod
    def clean_empty_date_strings(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v

    @field_validator("code")
    @classmethod
    def code_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Coupon code is required and cannot be empty.")
        return v.strip().upper()

    @field_validator("discount_percent")
    @classmethod
    def validate_discount_percent(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("Discount percentage must be between 0 and 100.")
        return v

    @field_validator("minimum_order_amount")
    @classmethod
    def validate_minimum_order(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Minimum order amount cannot be negative.")
        return v


class CouponUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    coupon_type: Optional[str] = None
    discount_type: Optional[str] = None
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None
    maximum_discount_amount: Optional[float] = None
    minimum_order_amount: Optional[float] = None
    start_at: Optional[str] = None
    expires_at: Optional[str] = None
    usage_limit: Optional[int] = None
    per_user_usage_limit: Optional[int] = None
    is_active: Optional[bool] = None
    
    eligibility_rule: Optional[str] = None
    eligibility_value: Optional[str] = None
    
    applicability: Optional[str] = None
    applicable_ids: Optional[List[str]] = None

    model_config = ConfigDict(extra="allow")


class CouponAdminResponse(BaseModel):
    id: str
    code: str
    name: Optional[str] = None
    description: str
    coupon_type: str = "CUSTOMER"
    discount_type: str
    discount_percent: float
    discount_amount: float
    maximum_discount_amount: float
    minimum_order_amount: float
    start_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_limit: int
    per_user_usage_limit: int
    is_active: bool
    status: str = "ACTIVE"
    created_at: datetime
    
    # Metadata for admin
    eligibility_rule: str = "ALL_USERS"
    eligibility_value: Optional[str] = None
    applicability: str = "ENTIRE_STORE"
    applicable_ids: List[str] = []
    usage_count: int = 0

    model_config = ConfigDict(from_attributes=True)

