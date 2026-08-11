import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/notifications", tags=["Admin Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Get admin notifications with filters and pagination",
)
async def get_admin_notifications(
    type: Optional[str] = Query(None, description="Notification type filter (all, orders, alerts, customers, system, new_order, low_stock, etc.)"),
    is_read: Optional[bool] = Query(None, description="Read status filter (true/false)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.get_admin_notifications(
        admin_id=current_user.id,
        type_filter=type,
        is_read_filter=is_read,
        page=page,
        limit=limit,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count for admin",
)
async def get_unread_notification_count(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.get_unread_count(admin_id=current_user.id)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark single notification as read",
)
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    res = await service.mark_as_read(notification_id=notification_id, admin_id=current_user.id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return res


@router.post(
    "/read-all",
    summary="Mark all admin notifications as read",
)
async def mark_all_notifications_as_read(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    count = await service.mark_all_as_read(admin_id=current_user.id)
    return {"message": "All notifications marked as read.", "updated_count": count}
