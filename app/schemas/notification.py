from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    type: str
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None


class NotificationCreate(NotificationBase):
    admin_id: Optional[str] = None


class NotificationResponse(BaseModel):
    id: str
    admin_id: Optional[str] = None
    type: str = "general"
    title: Optional[str] = "Notification"
    message: Optional[str] = ""
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    is_read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    limit: int
    unread_count: int
