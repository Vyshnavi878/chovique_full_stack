import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.db.base import Base


class InstagramReel(Base):
    __tablename__ = "instagram_reels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_url = Column(String(500), nullable=False)
    likes = Column(String(20), default="0", nullable=False)
    comments = Column(String(20), default="0", nullable=False)
    views = Column(String(20), default="0 views", nullable=False)
    title = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
