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
