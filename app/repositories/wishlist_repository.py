from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.wishlist import WishlistItem


class WishlistRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_wishlist(self, user_id: str) -> list[WishlistItem]:
        result = await self.db.execute(
            select(WishlistItem)
            .options(selectinload(WishlistItem.product))
            .where(WishlistItem.user_id == user_id)
            .order_by(WishlistItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_item(self, user_id: str, product_id: str) -> WishlistItem | None:
        # Check existing to prevent duplicate
        existing = await self.db.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            )
        )
        if existing.scalar_one_or_none():
            return None

        item = WishlistItem(user_id=user_id, product_id=product_id)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def remove_item(self, user_id: str, product_id: str) -> bool:
        result = await self.db.execute(
            delete(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_count(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(WishlistItem)
            .where(WishlistItem.user_id == user_id)
        )
        return result.scalar() or 0
