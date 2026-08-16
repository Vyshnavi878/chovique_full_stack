import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.base import Base


class Banner(Base):
    __tablename__ = "banners"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title = Column(String(255), nullable=False)
    subtitle = Column(Text, nullable=False)
    tag = Column(String(255), nullable=False)
    image = Column(Text, nullable=False)
    button_text = Column(String(100), nullable=False)
    link = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
