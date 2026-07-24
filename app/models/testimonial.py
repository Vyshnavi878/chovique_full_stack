import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
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
    author = Column(String(120), nullable=False)
    title = Column(String(200), nullable=True)
    text = Column(Text, nullable=False)
    rating = Column(Float, default=5.0, nullable=False)
    initials = Column(String(5), nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
