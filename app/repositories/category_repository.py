from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.category import Category


class CategoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> Category | None:
        result = await self.db.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Category | None:
        result = await self.db.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Category:
        category = Category(**kwargs)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update(self, category_id: str, **kwargs) -> Category | None:
        await self.db.execute(
            update(Category)
            .where(Category.id == category_id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_by_id(category_id)

    async def delete(self, category_id: str) -> bool:
        result = await self.db.execute(
            delete(Category).where(Category.id == category_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(select(func.count()).select_from(Category))
        return result.scalar() or 0
