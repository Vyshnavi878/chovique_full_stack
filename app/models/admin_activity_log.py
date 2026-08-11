import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class AdminActivityLog(Base):
    __tablename__ = "admin_activity_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="SUCCESS", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    admin = relationship("User", foreign_keys=[admin_id])
