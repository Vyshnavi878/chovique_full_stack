from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.reel import InstagramReel


class ReelRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_reels(self) -> list[InstagramReel]:
        result = await self.db.execute(
            select(InstagramReel)
            .where(InstagramReel.is_active.is_(True))
            .order_by(InstagramReel.sort_order.asc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs) -> InstagramReel:
        reel = InstagramReel(**kwargs)
        self.db.add(reel)
        await self.db.commit()
        await self.db.refresh(reel)
        return reel

    async def get_by_id(self, reel_id: str) -> InstagramReel | None:
        result = await self.db.execute(
            select(InstagramReel).where(InstagramReel.id == reel_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, reel_id: str) -> None:
        reel = await self.get_by_id(reel_id)
        if reel:
            await self.db.delete(reel)
            await self.db.commit()

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(select(func.count()).select_from(InstagramReel))
        return result.scalar() or 0

