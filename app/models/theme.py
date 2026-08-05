from sqlalchemy import Column, String, Text, Boolean
from app.db.base import Base

class ThemePreset(Base):
    __tablename__ = "theme_presets"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    # The JSON string representation of the CSS variables/properties
    properties_json = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False)
