import uuid
import random
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


def generate_ticket_id():
    return f"TKT-{random.randint(1000, 9999)}"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(String(36), primary_key=True, default=generate_ticket_id)
    customer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String(120), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="Pending", nullable=False)
    admin_notes = Column(Text, nullable=True)
    customer_resolution_feedback = Column(String(50), nullable=True)
    notified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    customer = relationship("User", backref="tickets")
