from typing import Optional
from pydantic import BaseModel, ConfigDict


class CouponValidationRequest(BaseModel):
    code: str


class CouponValidationResponse(BaseModel):
    valid: bool
    code: str
    discount_percent: float = 0.0
    discount_amount: Optional[float] = None
    message: str


class UserCouponResponse(BaseModel):
    code: str
    desc: str
    exp: str
    discountPercent: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CouponCreate(BaseModel):
    code: str
    description: str
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    expires_at: Optional[str] = None
    is_active: bool = True

class CouponUpdate(BaseModel):
    description: Optional[str] = None
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None

from datetime import datetime

class CouponAdminResponse(BaseModel):
    id: str
    code: str
    description: str
    discount_percent: float
    discount_amount: float
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
