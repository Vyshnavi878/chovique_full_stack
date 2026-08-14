from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ActivityLogResponse(BaseModel):
    id: str
    admin_id: Optional[str] = None
    admin_name: Optional[str] = "System Admin"
    admin_email: Optional[str] = None
    user_role: Optional[str] = "Admin"
    action: str
    module: str
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "SUCCESS"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityLogListResponse(BaseModel):
    items: List[ActivityLogResponse]
    total: int
    page: int
    limit: int
