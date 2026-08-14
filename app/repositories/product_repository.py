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
                )
            )

        if category and category != "all":
            from app.models.category import Category
            query = query.join(Product.category_rel, isouter=True).where(
                or_(
                    Product.category_id == category,
                    Category.id == category,
                    Category.slug == category,
                    Category.name.ilike(f"%{category}%")
                )
            )

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

    async def _resolve_category_id(self, category_id: str | None, legacy_cat: str | None) -> str | None:
        from app.models.category import Category
        val = category_id or legacy_cat
        if not val:
            return None

        # 1. Direct ID match
        res_id = await self.db.execute(select(Category.id).where(Category.id == val))
        matched_id = res_id.scalar_one_or_none()
        if matched_id:
            return matched_id

        # 2. Exact match on slug or name
        clean_val = val.strip()
        res_exact = await self.db.execute(
            select(Category.id).where(
                or_(
                    Category.slug == clean_val.lower(),
                    Category.name.ilike(clean_val)
                )
            ).order_by(Category.sort_order.asc())
        )
        matched_exact = res_exact.scalars().first()
        if matched_exact:
            return matched_exact

        # 3. Partial match on slug or name
        res_partial = await self.db.execute(
            select(Category.id).where(
                or_(
                    Category.slug.ilike(f"%{clean_val}%"),
                    Category.name.ilike(f"%{clean_val}%")
                )
            ).order_by(Category.sort_order.asc())
        )
        matched_partial = res_partial.scalars().first()
        if matched_partial:
            return matched_partial

        # 4. Fallback: Return first active category ID in database
        res_first = await self.db.execute(
            select(Category.id).where(Category.is_active.is_(True)).order_by(Category.sort_order.asc())
        )
        return res_first.scalars().first()

    # ==========================================================
    # Create
    # ==========================================================

    async def create(self, **kwargs) -> Product:
        category_id = kwargs.pop("category_id", None)
        legacy_cat = kwargs.pop("category", None)

        resolved_cat_id = await self._resolve_category_id(category_id, legacy_cat)

        product = Product(category_id=resolved_cat_id, **kwargs)
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
        category_id = kwargs.pop("category_id", None)
        legacy_cat = kwargs.pop("category", None)

        if category_id is not None or legacy_cat is not None:
            resolved_cat_id = await self._resolve_category_id(category_id, legacy_cat)
            if resolved_cat_id:
                kwargs["category_id"] = resolved_cat_id

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
