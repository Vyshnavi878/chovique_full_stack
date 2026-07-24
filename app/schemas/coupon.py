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
