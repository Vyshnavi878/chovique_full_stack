from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.faq import FAQ


class FAQRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_faqs(self) -> list[FAQ]:
        result = await self.db.execute(
            select(FAQ)
            .where(FAQ.is_active.is_(True))
            .order_by(FAQ.sort_order.asc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs) -> FAQ:
        faq = FAQ(**kwargs)
        self.db.add(faq)
        await self.db.commit()
        await self.db.refresh(faq)
        return faq

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(select(func.count()).select_from(FAQ))
        return result.scalar() or 0
