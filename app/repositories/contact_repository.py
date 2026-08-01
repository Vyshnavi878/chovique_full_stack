from sqlalchemy.ext.asyncio import AsyncSession
from app.models.contact import ContactMessage


class ContactRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> ContactMessage:
        message = ContactMessage(**kwargs)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_all(self) -> list[ContactMessage]:
        from sqlalchemy import select
        result = await self.db.execute(
            select(ContactMessage).order_by(ContactMessage.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, message_id: str) -> ContactMessage | None:
        from sqlalchemy import select
        result = await self.db.execute(
            select(ContactMessage).where(ContactMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, message_id: str) -> bool:
        msg = await self.get_by_id(message_id)
        if msg:
            await self.db.delete(msg)
            await self.db.commit()
            return True
        return False

