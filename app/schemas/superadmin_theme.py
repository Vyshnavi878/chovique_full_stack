import re
from typing import Optional, List
from pydantic import BaseModel, Field, validator

HEX_COLOR_REGEX = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")


class ThemeColors(BaseModel):
    primary_brand_color: str = Field(..., example="#5A3825")
    background_color: str = Field(..., example="#0D090A")
    luxury_gold_color: str = Field(..., example="#D4AF37")
    secondary_accent_color: str = Field(..., example="#B76E79")
    text_color: str = Field(..., example="#F7F7F7")
    surface_color: str = Field(..., example="#1A1716")

    @validator(
        "primary_brand_color",
        "background_color",
        "luxury_gold_color",
        "secondary_accent_color",
        "text_color",
        "surface_color",
        pre=True,
    )
    def validate_hex_color(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Color value is required.")
        v_clean = v.strip()
        if not HEX_COLOR_REGEX.match(v_clean):
            raise ValueError(f"Invalid HEX color format: '{v_clean}'. Expected #RRGGBB format.")
        return v_clean.upper()


class ThemeCreateRequest(ThemeColors):
    name: str = Field(..., min_length=2, max_length=120, example="Custom Gold Luxury")
    description: Optional[str] = Field(None, example="Custom theme palette created by Superadmin")


class ThemeUpdateRequest(ThemeColors):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = None


class ThemeResponse(ThemeColors):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool = False
    is_preset: bool = False
    created_at: str
    updated_at: str
    created_by: Optional[str] = None


class ThemeListResponse(BaseModel):
    items: List[ThemeResponse] = Field(default_factory=list)
    active_theme_id: Optional[str] = None
