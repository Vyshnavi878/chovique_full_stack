from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.banner import Banner


class BannerRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # Get Active Banners
    # ==========================================================

    async def get_active(self) -> list[Banner]:

        result = await self.db.execute(
            select(Banner)
            .where(Banner.is_active.is_(True))
            .order_by(Banner.sort_order.asc())
        )

        return list(result.scalars().all())

    # ==========================================================
    # Create
    # ==========================================================

    async def create(self, **kwargs) -> Banner:

        banner = Banner(**kwargs)
        self.db.add(banner)
        await self.db.commit()
        await self.db.refresh(banner)
        return banner

    # ==========================================================
    # Get By ID
    # ==========================================================

    async def get_by_id(self, banner_id: str) -> Banner | None:
        result = await self.db.execute(
            select(Banner).where(Banner.id == banner_id)
        )
        return result.scalar_one_or_none()

    # ==========================================================
    # Update
    # ==========================================================

    async def update(self, banner: Banner, **kwargs) -> Banner:
        for key, value in kwargs.items():
            if hasattr(banner, key):
                setattr(banner, key, value)
        
        await self.db.commit()
        await self.db.refresh(banner)
        return banner

    # ==========================================================
    # Delete
    # ==========================================================

    async def delete(self, banner_id: str) -> bool:
        banner = await self.get_by_id(banner_id)
        if not banner:
            return False
        await self.db.delete(banner)
        await self.db.commit()
        return True

    # ==========================================================
    # Count
    # ==========================================================

    async def count(self) -> int:

        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count()).select_from(Banner)
        )

        return result.scalar() or 0

