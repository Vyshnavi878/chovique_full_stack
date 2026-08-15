from typing import Optional
from pydantic import BaseModel, ConfigDict


class CreateTicketPayload(BaseModel):
    category: str
    description: str
    order_id: Optional[str] = None
    orderId: Optional[str] = None


class TicketFeedbackPayload(BaseModel):
    feedback: str  # 'Resolved' | 'Not Resolved'


class SupportTicketResponse(BaseModel):
    id: str
    customerId: str
    customerName: str
    category: str
    description: str
    status: str
    orderId: Optional[str] = None
    order_id: Optional[str] = None
    adminNotes: Optional[str] = None
    customerResolutionFeedback: Optional[str] = None
    date: str
    notified: bool

    model_config = ConfigDict(from_attributes=True)
