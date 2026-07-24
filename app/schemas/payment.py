from typing import Optional
from pydantic import BaseModel, ConfigDict


class VerifyPaymentPayload(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentResponseSchema(BaseModel):
    id: str
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: Optional[str] = None
    amount: float
    currency: str
    status: str

    model_config = ConfigDict(from_attributes=True)
