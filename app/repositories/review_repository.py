from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.review import ProductReview


class ReviewRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_product_reviews(self, product_id: str) -> list[ProductReview]:
        result = await self.db.execute(
            select(ProductReview)
            .where(ProductReview.product_id == product_id)
            .order_by(ProductReview.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ProductReview:
        review = ProductReview(**kwargs)
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(select(func.count()).select_from(ProductReview))
        return result.scalar() or 0
