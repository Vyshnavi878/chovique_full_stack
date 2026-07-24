import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.db.base import Base


class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question = Column(String(300), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), default="General", nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
