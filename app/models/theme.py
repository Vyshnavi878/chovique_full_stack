import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class ThemePreset(Base):
    __tablename__ = "theme_presets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Core color configuration fields
    primary_brand_color = Column(String(20), nullable=False, default="#5A3825")
    background_color = Column(String(20), nullable=False, default="#0D090A")
    luxury_gold_color = Column(String(20), nullable=False, default="#D4AF37")
    secondary_accent_color = Column(String(20), nullable=False, default="#B76E79")
    text_color = Column(String(20), nullable=False, default="#F7F7F7")
    surface_color = Column(String(20), nullable=False, default="#1A1716")

    # Legacy properties string (for backward compatibility)
    properties_json = Column(Text, nullable=True)

    is_active = Column(Boolean, default=False, nullable=False, index=True)
    is_preset = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
