from typing import Optional, List
from pydantic import BaseModel, ConfigDict
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
    code: str
    name: Optional[str] = None
    description: str
    discount_type: str = "PERCENTAGE"
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    maximum_discount_amount: float = 0.0
    minimum_order_amount: float = 0.0
    start_at: Optional[str] = None
    expires_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CouponCreate(BaseModel):
    code: str
    name: Optional[str] = None
    description: str
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


class CouponUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
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


class CouponAdminResponse(BaseModel):
    id: str
    code: str
    name: Optional[str] = None
    description: str
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
    created_at: datetime
    
    # Metadata for admin
    eligibility_rule: str = "ALL_USERS"
    eligibility_value: Optional[str] = None
    applicability: str = "ENTIRE_STORE"
    applicable_ids: List[str] = []
    usage_count: int = 0

    model_config = ConfigDict(from_attributes=True)

