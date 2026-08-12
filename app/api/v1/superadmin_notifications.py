"""FastAPI Router — Superadmin Notifications."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.superadmin_notifications import (
    SuperadminNotificationListResponse,
    SuperadminNotificationResponse,
    UnreadCountResponse,
)
from app.services.superadmin_notification_service import SuperadminNotificationService

router = APIRouter(
    prefix="/superadmin/notifications",
    tags=["Superadmin Notifications"],
)


@router.get(
    "",
    response_model=SuperadminNotificationListResponse,
    summary="Get paginated superadmin notifications",
    description="Fetch superadmin notifications filtered by category, severity, read status, date range, or search query.",
)
async def list_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="SECURITY, ADMIN_MANAGEMENT, PLATFORM_SYSTEM, BUSINESS"),
    severity: Optional[str] = Query(None, description="INFO, WARNING, CRITICAL"),
    is_read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD start date"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD end date"),
    search: Optional[str] = Query(None, description="Search title or message"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> SuperadminNotificationListResponse:
    service = SuperadminNotificationService(db)
    return await service.list_notifications(
        page=page,
        limit=limit,
        category=category,
        severity=severity,
        is_read=is_read,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notifications count",
    description="Return total count of unread superadmin notifications.",
)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> UnreadCountResponse:
    service = SuperadminNotificationService(db)
    return await service.get_unread_count()


@router.get(
    "/{notification_id}",
    response_model=SuperadminNotificationResponse,
    summary="Get notification details by ID",
)
async def get_notification_by_id(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> SuperadminNotificationResponse:
    service = SuperadminNotificationService(db)
    return await service.get_by_id(notification_id)


@router.patch(
    "/{notification_id}/read",
    response_model=SuperadminNotificationResponse,
    summary="Mark single notification as read",
)
async def mark_as_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> SuperadminNotificationResponse:
    service = SuperadminNotificationService(db)
    return await service.mark_as_read(notification_id)


@router.patch(
    "/read-all",
    response_model=UnreadCountResponse,
    summary="Mark all superadmin notifications as read",
)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> UnreadCountResponse:
    service = SuperadminNotificationService(db)
    return await service.mark_all_as_read()


@router.delete(
    "/{notification_id}",
    summary="Delete superadmin notification",
)
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> dict:
    service = SuperadminNotificationService(db)
    return await service.delete_notification(notification_id)
