from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.testimonial import Testimonial


class TestimonialRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # Get Approved / Active Testimonials (Public for Home + Our Story)
    # ==========================================================

    async def get_active(self) -> list[Testimonial]:
        result = await self.db.execute(
            select(Testimonial)
            .where(
                or_(
                    Testimonial.is_active.is_(True),
                    Testimonial.status == "approved"
                )
            )
            .order_by(Testimonial.sort_order.asc(), Testimonial.created_at.desc())
        )
        return list(result.scalars().all())

    # ==========================================================
    # Get All for Admin (Supports status filter: pending, approved, rejected)
    # ==========================================================

    async def get_all_for_admin(self, status: str | None = None) -> list[Testimonial]:
        query = select(Testimonial)
        if status and status != "all":
            query = query.where(Testimonial.status == status)
        query = query.order_by(Testimonial.created_at.desc())

        result = await self.db.execute(query)
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

    async def update_status(self, testimonial_id: str, status: str) -> Testimonial | None:
        is_active = (status == "approved")
        await self.db.execute(
            update(Testimonial)
            .where(Testimonial.id == testimonial_id)
            .values(status=status, is_active=is_active)
        )
        await self.db.commit()
        return await self.get_by_id(testimonial_id)

    async def delete(self, testimonial_id: str) -> bool:
        item = await self.get_by_id(testimonial_id)
        if item:
            await self.db.delete(item)
            await self.db.commit()
            return True
        return False

    # ==========================================================
    # Count
    # ==========================================================

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(Testimonial)
        )
        return result.scalar() or 0
