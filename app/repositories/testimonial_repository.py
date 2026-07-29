from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.testimonial import Testimonial


class TestimonialRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # Get Active Testimonials
    # ==========================================================

    async def get_active(self) -> list[Testimonial]:

        result = await self.db.execute(
            select(Testimonial)
            .where(Testimonial.is_active.is_(True))
            .order_by(Testimonial.sort_order.asc())
        )

        return list(result.scalars().all())

    # ==========================================================
    # Create
    # ==========================================================

    async def create(self, **kwargs) -> Testimonial:

        testimonial = Testimonial(**kwargs)
        self.db.add(testimonial)
        await self.db.commit()
        await self.db.refresh(testimonial)
        return testimonial

    async def get_by_id(self, testimonial_id: str) -> Testimonial | None:
        result = await self.db.execute(
            select(Testimonial).where(Testimonial.id == testimonial_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, testimonial_id: str) -> None:
        item = await self.get_by_id(testimonial_id)
        if item:
            await self.db.delete(item)
            await self.db.commit()

    # ==========================================================
    # Count
    # ==========================================================

    async def count(self) -> int:

        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count()).select_from(Testimonial)
        )

        return result.scalar() or 0

