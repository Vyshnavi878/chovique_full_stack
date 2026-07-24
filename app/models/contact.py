import uuid
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func
from app.db.base import Base


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False)
    email = Column(String(254), nullable=False)
    phone = Column(String(30), nullable=True)
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
