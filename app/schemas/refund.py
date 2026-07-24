from typing import Optional
from pydantic import BaseModel, ConfigDict


class InitiateRefundPayload(BaseModel):
    order_id: str
    amount: Optional[float] = None
    reason: Optional[str] = "Customer request / Return"


class RefundResponseSchema(BaseModel):
    id: str
    order_id: str
    razorpay_refund_id: Optional[str] = None
    amount: float
    reason: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)
