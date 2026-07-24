from typing import Optional
from pydantic import BaseModel, EmailStr


class ContactMessageRequest(BaseModel):
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    subject: Optional[str] = "General Inquiry"
    message: str


class ContactMessageResponse(BaseModel):
    message: str
