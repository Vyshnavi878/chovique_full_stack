import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, String, Text
from sqlalchemy.sql import func
from app.db.base import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    discount_percent = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
