import math
from typing import Any

from sqlalchemy import func, or_, select, update, delete, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # Get All (Paginated + Filtered)
    # ==========================================================

    async def get_all(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        min_rating: float | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 12,
    ) -> dict[str, Any]:

        query = select(Product).where(Product.is_active.is_(True))

        # --- Filters ---

        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Product.name.ilike(term),
                    Product.description.ilike(term),
                    Product.ingredients.ilike(term),
                    Product.badge.ilike(term),
                    cast(Product.category, String).ilike(term),
                )
            )

        if category and category != "all":
            valid_enums = ["dark", "milk", "white", "gift", "beverage"]
            if category in valid_enums:
                query = query.where(Product.category == category)
            else:
                query = query.where(cast(Product.category, String).ilike(f"%{category}%"))

        if price_min is not None:
            query = query.where(Product.price >= price_min)

        if price_max is not None:
            query = query.where(Product.price <= price_max)

        if min_rating is not None:
            query = query.where(Product.rating >= min_rating)

        if sort in ("newest", "new"):
            query = query.where(
                or_(
                    Product.is_new_arrival.is_(True),
                    Product.badge.in_(["New", "Limited"]),
                )
            )
        elif sort == "bestseller":
            query = query.where(
                or_(
                    Product.is_bestseller.is_(True),
                    Product.badge.in_(["Bestseller", "Premium"]),
                )
            )

        # --- Count (before pagination) ---

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # --- Sort ---

        sort_map = {
            "price_asc": Product.price.asc(),
            "price_desc": Product.price.desc(),
            "rating": Product.rating.desc(),
            "newest": Product.created_at.desc(),
            "name_asc": Product.name.asc(),
            "name_desc": Product.name.desc(),
        }

        order = sort_map.get(sort, Product.sort_order.asc())
        query = query.order_by(order)

        # --- Pagination ---

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    # ==========================================================
    # Get By ID
    # ==========================================================

    async def get_by_id(self, product_id: str) -> Product | None:

        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # Get By Slug
    # ==========================================================

    async def get_by_slug(self, slug: str) -> Product | None:

        result = await self.db.execute(
            select(Product).where(Product.slug == slug)
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # Get Featured (Top Rated)
    # ==========================================================

    async def get_featured(self, limit: int = 4) -> list[Product]:

        result = await self.db.execute(
            select(Product)
            .where(Product.is_active.is_(True))
            .order_by(Product.sort_order.asc(), Product.rating.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

    # ==========================================================
    # Get Bestsellers
    # ==========================================================

    async def get_bestsellers(self, limit: int = 4) -> list[Product]:

        result = await self.db.execute(
            select(Product)
            .where(
                Product.is_active.is_(True),
                or_(
                    Product.badge.in_(["Bestseller", "Premium"]),
                    Product.is_bestseller.is_(True),
                ),
            )
            .order_by(Product.rating.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

    # ==========================================================
    # Get New Arrivals
    # ==========================================================

    async def get_new_arrivals(self, limit: int = 4) -> list[Product]:

        result = await self.db.execute(
            select(Product)
            .where(
                Product.is_active.is_(True),
                or_(
                    Product.badge.in_(["New", "Limited"]),
                    Product.is_new_arrival.is_(True),
                ),
            )
            .order_by(Product.created_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

    # ==========================================================
    # Get By Category
    # ==========================================================

    async def get_by_category(
        self,
        category: str,
        limit: int = 10,
    ) -> list[Product]:

        result = await self.db.execute(
            select(Product)
            .where(
                Product.is_active.is_(True),
                Product.category == category,
            )
            .order_by(Product.sort_order.asc())
            .limit(limit)
        )

        return list(result.scalars().all())

    # ==========================================================
    # Create
    # ==========================================================

    async def create(self, **kwargs) -> Product:

        product = Product(**kwargs)
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product

    # ==========================================================
    # Update
    # ==========================================================

    async def update(
        self,
        product_id: str,
        commit: bool = True,
        **kwargs,
    ) -> Product | None:

        if kwargs:
            await self.db.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(**kwargs)
            )

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        return await self.get_by_id(product_id)

    # ==========================================================
    # Delete
    # ==========================================================

    async def delete(self, product_id: str) -> None:
        from app.models.cart import CartItem
        from app.models.wishlist import WishlistItem

        await self.db.execute(delete(CartItem).where(CartItem.product_id == product_id))
        await self.db.execute(delete(WishlistItem).where(WishlistItem.product_id == product_id))
        await self.db.execute(delete(Product).where(Product.id == product_id))
        await self.db.commit()

    # ==========================================================
    # Count
    # ==========================================================

    async def count(self) -> int:

        result = await self.db.execute(
            select(func.count()).select_from(Product)
        )

        return result.scalar() or 0
