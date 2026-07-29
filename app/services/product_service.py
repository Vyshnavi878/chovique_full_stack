import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    PaginatedProductResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Generate a URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


class ProductService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)

    # ==========================================================
    # List Products (Paginated + Filtered)
    # ==========================================================

    async def list_products(
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
    ) -> PaginatedProductResponse:

        result = await self.product_repo.get_all(
            search=search,
            category=category,
            price_min=price_min,
            price_max=price_max,
            min_rating=min_rating,
            sort=sort,
            page=page,
            per_page=per_page,
        )

        return PaginatedProductResponse(
            items=[
                ProductResponse.from_orm_model(p)
                for p in result["items"]
            ],
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"],
        )

    # ==========================================================
    # Get Single Product
    # ==========================================================

    async def get_product(self, product_id: str) -> ProductResponse | None:

        product = await self.product_repo.get_by_id(product_id)

        if not product:
            return None

        return ProductResponse.from_orm_model(product)

    # ==========================================================
    # Create Product
    # ==========================================================

    async def create_product(
        self,
        data: ProductCreate,
    ) -> ProductResponse:

        slug = _slugify(data.name)

        # Check for duplicate slug
        existing = await self.product_repo.get_by_slug(slug)
        if existing:
            # Append a counter
            import uuid
            slug = f"{slug}-{str(uuid.uuid4())[:8]}"

        nutrition_dict = None
        if data.nutrition:
            nutrition_dict = data.nutrition.model_dump()

        product = await self.product_repo.create(
            name=data.name,
            slug=slug,
            category=data.category,
            price=data.price,
            original_price=data.original_price,
            weight=data.weight,
            stock=data.stock,
            description=data.description,
            ingredients=data.ingredients,
            nutrition=nutrition_dict,
            badge=data.badge,
            image=data.image,
            hover_image=data.hover_image,
            rating=data.rating,
            ratings_count=data.ratings_count,
            sort_order=data.sort_order,
            is_featured=data.is_featured,
            is_bestseller=data.is_bestseller,
            is_new_arrival=data.is_new_arrival,
        )

        logger.info("Product created: id=%s name=%s", product.id, product.name)

        return ProductResponse.from_orm_model(product)

    # ==========================================================
    # Update Product
    # ==========================================================

    async def update_product(
        self,
        product_id: str,
        data: ProductUpdate,
    ) -> ProductResponse | None:

        existing = await self.product_repo.get_by_id(product_id)

        if not existing:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle nutrition serialization
        if "nutrition" in update_data and update_data["nutrition"]:
            update_data["nutrition"] = update_data["nutrition"].model_dump() if hasattr(update_data["nutrition"], "model_dump") else update_data["nutrition"]

        if not update_data:
            return ProductResponse.from_orm_model(existing)

        product = await self.product_repo.update(
            product_id,
            **update_data,
        )

        logger.info("Product updated: id=%s", product_id)

        return ProductResponse.from_orm_model(product)

    # ==========================================================
    # Delete Product
    # ==========================================================

    async def delete_product(self, product_id: str) -> bool:

        existing = await self.product_repo.get_by_id(product_id)

        if not existing:
            return False

        await self.product_repo.delete(product_id)

        logger.info("Product deleted: id=%s", product_id)

        return True
