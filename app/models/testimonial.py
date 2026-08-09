import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.base import Base


class Testimonial(Base):
    __tablename__ = "testimonials"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    author = Column(String(120), nullable=False)
    title = Column(String(200), nullable=True)
    text = Column(Text, nullable=False)
    rating = Column(Float, default=5.0, nullable=False)
    initials = Column(String(5), nullable=True)
    avatar_url = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    is_active = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
