import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id = Column(String(36), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    razorpay_refund_id = Column(String(100), unique=True, nullable=True, index=True)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(50), default="processed", nullable=False)  # pending, processed, failed

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", backref="refunds")
    payment = relationship("Payment")
