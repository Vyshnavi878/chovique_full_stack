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
    # Count
    # ==========================================================

    async def count(self) -> int:

        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count()).select_from(Banner)
        )

        return result.scalar() or 0
