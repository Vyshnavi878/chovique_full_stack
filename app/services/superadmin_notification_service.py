"""
Superadmin Notification Service.

This module provides:
  1. A reusable notification creation API (create_*_notification helpers).
  2. CRUD service for reading/marking/deleting notifications.

The create_* helpers are designed to be imported and called from other
services/routers (auth, admin management, platform settings, etc.) whenever
an owner-level event occurs.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.superadmin_notification import SuperadminNotification
from app.schemas.superadmin_notifications import (
    SuperadminNotificationCreate,
    SuperadminNotificationListResponse,
    SuperadminNotificationResponse,
    UnreadCountResponse,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Reusable notification creators — callable from any module
# ──────────────────────────────────────────────────────────────────────────────

async def create_security_notification(
    db: AsyncSession,
    title: str,
    message: str,
    severity: str = "WARNING",
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
) -> None:
    """Create a SECURITY category superadmin notification (fire-and-forget)."""
    await _create(db, SuperadminNotificationCreate(
        title=title,
        message=message,
        category="SECURITY",
        severity=severity,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        related_user_id=related_user_id,
    ))


async def create_admin_management_notification(
    db: AsyncSession,
    title: str,
    message: str,
    severity: str = "INFO",
    related_entity_type: str = "admin_user",
    related_entity_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
) -> None:
    """Create an ADMIN_MANAGEMENT category superadmin notification."""
    await _create(db, SuperadminNotificationCreate(
        title=title,
        message=message,
        category="ADMIN_MANAGEMENT",
        severity=severity,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        related_user_id=related_user_id,
    ))


async def create_platform_notification(
    db: AsyncSession,
    title: str,
    message: str,
    severity: str = "WARNING",
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
) -> None:
    """Create a PLATFORM_SYSTEM category superadmin notification."""
    await _create(db, SuperadminNotificationCreate(
        title=title,
        message=message,
        category="PLATFORM_SYSTEM",
        severity=severity,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        related_user_id=related_user_id,
    ))


async def create_business_notification(
    db: AsyncSession,
    title: str,
    message: str,
    severity: str = "WARNING",
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
) -> None:
    """Create a BUSINESS category superadmin notification."""
    await _create(db, SuperadminNotificationCreate(
        title=title,
        message=message,
        category="BUSINESS",
        severity=severity,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        related_user_id=related_user_id,
    ))


async def _create(db: AsyncSession, payload: SuperadminNotificationCreate) -> None:
    """Internal helper — insert one notification row, silently ignoring errors."""
    try:
        notif = SuperadminNotification(
            title=payload.title,
            message=payload.message,
            category=payload.category,
            severity=payload.severity,
            related_entity_type=payload.related_entity_type,
            related_entity_id=payload.related_entity_id,
            related_user_id=payload.related_user_id,
        )
        db.add(notif)
        await db.commit()
    except Exception as exc:
        logger.error("Failed to create superadmin notification: %s", exc)
        await db.rollback()


# ──────────────────────────────────────────────────────────────────────────────
# CRUD service used by the API router
# ──────────────────────────────────────────────────────────────────────────────

class SuperadminNotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── List notifications (paginated + filtered) ──────────────────────────

    async def list_notifications(
        self,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        is_read: Optional[bool] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
    ) -> SuperadminNotificationListResponse:
        from sqlalchemy import and_, or_

        q = (
            select(SuperadminNotification)
            .options(selectinload(SuperadminNotification.related_user))
        )
        filters = []

        if category:
            filters.append(SuperadminNotification.category == category.upper())
        if severity:
            filters.append(SuperadminNotification.severity == severity.upper())
        if is_read is not None:
            filters.append(SuperadminNotification.is_read == is_read)
        if date_from:
            try:
                from datetime import date
                dt = datetime.strptime(date_from, "%Y-%m-%d")
                filters.append(SuperadminNotification.created_at >= dt)
            except ValueError:
                pass
        if date_to:
            try:
                from datetime import date
                dt = datetime.strptime(date_to, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
                filters.append(SuperadminNotification.created_at <= dt)
            except ValueError:
                pass
        if search:
            term = f"%{search}%"
            filters.append(
                or_(
                    SuperadminNotification.title.ilike(term),
                    SuperadminNotification.message.ilike(term),
                )
            )

        if filters:
            q = q.where(and_(*filters))

        # Total count
        count_q = select(func.count()).select_from(
            q.order_by(None).subquery()
        )
        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        # Unread count (global, not filtered)
        unread_result = await self.db.execute(
            select(func.count()).where(
                SuperadminNotification.is_read == False  # noqa: E712
            )
        )
        unread_count = unread_result.scalar_one()

        # Paginate
        q = q.order_by(SuperadminNotification.created_at.desc())
        q = q.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(q)
        items = result.scalars().all()

        total_pages = max(1, (total + limit - 1) // limit)

        return SuperadminNotificationListResponse(
            items=[SuperadminNotificationResponse.model_validate(n) for n in items],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            unread_count=unread_count,
        )

    # ── Unread count ───────────────────────────────────────────────────────

    async def get_unread_count(self) -> UnreadCountResponse:
        result = await self.db.execute(
            select(func.count()).where(
                SuperadminNotification.is_read == False  # noqa: E712
            )
        )
        return UnreadCountResponse(unread_count=result.scalar_one())

    # ── Single notification ────────────────────────────────────────────────

    async def get_by_id(self, notification_id: str) -> SuperadminNotificationResponse:
        from fastapi import HTTPException, status

        result = await self.db.execute(
            select(SuperadminNotification)
            .options(selectinload(SuperadminNotification.related_user))
            .where(SuperadminNotification.id == notification_id)
        )
        notif = result.scalar_one_or_none()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        return SuperadminNotificationResponse.model_validate(notif)

    # ── Mark one as read ──────────────────────────────────────────────────

    async def mark_as_read(self, notification_id: str) -> SuperadminNotificationResponse:
        from fastapi import HTTPException, status

        result = await self.db.execute(
            select(SuperadminNotification).where(
                SuperadminNotification.id == notification_id
            )
        )
        notif = result.scalar_one_or_none()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(notif)
        return SuperadminNotificationResponse.model_validate(notif)

    # ── Mark all as read ──────────────────────────────────────────────────

    async def mark_all_as_read(self) -> UnreadCountResponse:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(SuperadminNotification)
            .where(SuperadminNotification.is_read == False)  # noqa: E712
            .values(is_read=True, read_at=now)
        )
        await self.db.commit()
        return UnreadCountResponse(unread_count=0)

    # ── Delete ────────────────────────────────────────────────────────────

    async def delete_notification(self, notification_id: str) -> dict:
        from fastapi import HTTPException, status

        result = await self.db.execute(
            select(SuperadminNotification).where(
                SuperadminNotification.id == notification_id
            )
        )
        notif = result.scalar_one_or_none()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )
        await self.db.delete(notif)
        await self.db.commit()
        return {"message": "Notification deleted successfully."}
