from typing import Optional
from pydantic import BaseModel, ConfigDict


class CreateTicketPayload(BaseModel):
    category: str
    description: str


class TicketFeedbackPayload(BaseModel):
    feedback: str  # 'Resolved' | 'Not Resolved'


class SupportTicketResponse(BaseModel):
    id: str
    customerId: str
    customerName: str
    category: str
    description: str
    status: str
    adminNotes: Optional[str] = None
    customerResolutionFeedback: Optional[str] = None
    date: str
    notified: bool

    model_config = ConfigDict(from_attributes=True)
