from sqlalchemy import delete, select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification


class NotificationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_notifications(self, user_id: str, is_read: bool | None = None) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if is_read is False:
            query = query.where((Notification.is_read == False) & (Notification.read == False))
        elif is_read is True:
            query = query.where((Notification.is_read == True) | (Notification.read == True))
        query = query.order_by(Notification.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, notification_id: str) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def create(self, commit: bool = True, **kwargs) -> Notification:
        notification = Notification(**kwargs)
        self.db.add(notification)
        if commit:
            await self.db.commit()
            await self.db.refresh(notification)
        else:
            await self.db.flush()
        return notification

    async def mark_read(self, notification_id: str, user_id: str) -> Notification | None:
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(read=True, is_read=True)
        )
        await self.db.commit()
        return await self.get_by_id(notification_id)

    async def get_user_unread_count(self, user_id: str) -> int:
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            (Notification.is_read == False) & (Notification.read == False)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def mark_user_read_all(self, user_id: str) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                (Notification.is_read == False) | (Notification.read == False)
            )
            .values(is_read=True, read=True)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount

    async def delete(self, notification_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            delete(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ======================================================
    # ADMIN NOTIFICATIONS
    # ======================================================

    async def get_admin_notifications(
        self,
        admin_id: str,
        type_filter: str | None = None,
        is_read_filter: bool | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Notification], int]:
        query = select(Notification).where(
            (Notification.admin_id == admin_id) | (Notification.admin_id.is_(None))
        )

        if type_filter and type_filter.lower() != 'all':
            tf = type_filter.lower()
            if tf in ('orders', 'order'):
                query = query.where(
                    (func.lower(Notification.type).like('%order%')) |
                    (func.lower(Notification.type).like('%payment%'))
                )
            elif tf in ('alerts', 'alert'):
                query = query.where(
                    (func.lower(Notification.type).like('%stock%')) |
                    (func.lower(Notification.type).like('%alert%')) |
                    (func.lower(Notification.type) == 'warning')
                )
            elif tf in ('customers', 'customer'):
                query = query.where(
                    (func.lower(Notification.type).like('%customer%')) |
                    (func.lower(Notification.type).like('%user%'))
                )
            elif tf == 'system':
                query = query.where(
                    (func.lower(Notification.type).like('%system%')) |
                    (func.lower(Notification.type).like('%platform%')) |
                    (func.lower(Notification.type) == 'general') |
                    (func.lower(Notification.type) == 'support_message') |
                    (func.lower(Notification.type) == 'coupon_usage') |
                    (func.lower(Notification.type) == 'reward_adjustment')
                )
            else:
                query = query.where(func.lower(Notification.type) == tf)

        if is_read_filter is not None:
            query = query.where(Notification.is_read == is_read_filter)

        # Count total
        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        # Paginate
        query = query.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_admin_unread_count(self, admin_id: str) -> int:
        query = select(func.count(Notification.id)).where(
            ((Notification.admin_id == admin_id) | (Notification.admin_id.is_(None))),
            Notification.is_read == False
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def mark_admin_read(self, notification_id: str, admin_id: str) -> Notification | None:
        query = select(Notification).where(
            Notification.id == notification_id,
            (Notification.admin_id == admin_id) | (Notification.admin_id.is_(None))
        )
        res = await self.db.execute(query)
        notif = res.scalar_one_or_none()
        if notif:
            notif.is_read = True
            notif.read = True
            await self.db.commit()
            await self.db.refresh(notif)
        return notif

    async def mark_admin_read_all(self, admin_id: str) -> int:
        stmt = (
            update(Notification)
            .where(
                (Notification.admin_id == admin_id) | (Notification.admin_id.is_(None)),
                Notification.is_read == False
            )
            .values(is_read=True, read=True)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount

    async def create_admin_notification_if_not_exists(
        self,
        admin_id: str | None,
        type: str,
        title: str,
        message: str,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
        commit: bool = True,
    ) -> Notification | None:
        # Check duplicate (only if an active unread notification exists)
        if related_entity_type and related_entity_id:
            check_q = select(Notification).where(
                Notification.type == type,
                Notification.related_entity_type == related_entity_type,
                Notification.related_entity_id == related_entity_id,
                Notification.is_read == False,
            )
            if admin_id:
                check_q = check_q.where(Notification.admin_id == admin_id)

            existing = (await self.db.execute(check_q)).scalar_one_or_none()
            if existing:
                return existing

        notif = Notification(
            admin_id=admin_id,
            type=type,
            title=title,
            message=message,
            text=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            is_read=False,
            read=False,
        )
        self.db.add(notif)
        if commit:
            await self.db.commit()
            await self.db.refresh(notif)
        else:
            await self.db.flush()
        return notif
