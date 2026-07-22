import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column( String(36), primary_key=True, default=lambda: str(uuid.uuid4()),)
    user_id = Column(String(36),ForeignKey("users.id", ondelete="CASCADE"),nullable=False,index=True,)
    jti = Column(String(36),unique=True,nullable=False,index=True,default=lambda: str(uuid.uuid4()))
    hashed_token = Column(Text,nullable=False)
    device_info = Column(Text,nullable=True,)
    ip_address = Column( String(50),nullable=True,)
    user_agent = Column(Text,nullable=True,)
    expires_at = Column(DateTime(timezone=True),nullable=False,)
    revoked_at = Column(DateTime(timezone=True), nullable=True, )
    created_at = Column(DateTime(timezone=True),server_default=func.now(),nullable=False,)

    user = relationship( "User", back_populates="refresh_tokens",)