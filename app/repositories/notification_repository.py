from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification


class NotificationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_notifications(self, user_id: str) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, notification_id: str) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Notification:
        notification = Notification(**kwargs)
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_read(self, notification_id: str, user_id: str) -> Notification | None:
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(read=True)
        )
        await self.db.commit()
        return await self.get_by_id(notification_id)

    async def delete(self, notification_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            delete(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount > 0
