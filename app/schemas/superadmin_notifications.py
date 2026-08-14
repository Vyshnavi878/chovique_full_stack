"""Pydantic schemas for Superadmin Notifications."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

VALID_CATEGORIES = {"SECURITY", "ADMIN_MANAGEMENT", "PLATFORM_SYSTEM", "BUSINESS"}
VALID_SEVERITIES = {"INFO", "WARNING", "CRITICAL"}


# ──────────────────────────────────────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field, AliasChoices


class RelatedUserInfo(BaseModel):
    id: str
    name: str = Field(default="", validation_alias=AliasChoices("name", "full_name"))
    email: str
    role: str

    model_config = {"from_attributes": True}


class SuperadminNotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    category: str
    severity: str
    is_read: bool
    read_at: Optional[datetime] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    related_user_id: Optional[str] = None
    related_user: Optional[RelatedUserInfo] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SuperadminNotificationListResponse(BaseModel):
    items: List[SuperadminNotificationResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


# ──────────────────────────────────────────────────────────────────────────────
# Internal creation schema (used by the notification service)
# ──────────────────────────────────────────────────────────────────────────────

class SuperadminNotificationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    message: str = Field(..., min_length=1)
    category: str  # SECURITY | ADMIN_MANAGEMENT | PLATFORM_SYSTEM | BUSINESS
    severity: str = "INFO"  # INFO | WARNING | CRITICAL
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    related_user_id: Optional[str] = None
