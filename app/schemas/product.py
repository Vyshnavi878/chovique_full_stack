from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ==========================================================
# Nutrition Info
# ==========================================================

class NutritionInfo(BaseModel):
    calories: str = ""
    totalFat: str = ""
    saturatedFat: str = ""
    cholesterol: str = ""
    sodium: str = ""
    totalCarb: str = ""
    protein: str = ""


# ==========================================================
# Review Response
# ==========================================================

class ReviewResponse(BaseModel):
    id: str
    author: str
    rating: float
    text: str
    date: str
    avatar: Optional[str] = None


# ==========================================================
# Product Response
# ==========================================================

class ProductResponse(BaseModel):
    id: str
    name: str
    slug: str
    category: str
    price: float
    originalPrice: Optional[float] = None
    weight: Optional[str] = None
    description: Optional[str] = None
    ingredients: Optional[str] = None
    nutrition: Optional[NutritionInfo] = None
    badge: Optional[str] = None
    image: Optional[str] = None
    hoverImage: Optional[str] = None
    rating: float = 0.0
    ratingsCount: int = 0
    reviews: list[ReviewResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, product) -> "ProductResponse":
        """Convert an ORM Product to a frontend-compatible response."""

        nutrition = None
        if product.nutrition:
            nutrition = NutritionInfo(**product.nutrition)

        reviews = []
        if hasattr(product, "reviews_list") and product.reviews_list:
            reviews = [
                ReviewResponse(
                    id=r.id,
                    author=r.author,
                    rating=r.rating,
                    text=r.text,
                    date=r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
                    avatar=r.avatar,
                )
                for r in product.reviews_list
            ]

        return cls(
            id=product.id,
            name=product.name,
            slug=product.slug,
            category=product.category,
            price=product.price,
            originalPrice=product.original_price,
            weight=product.weight,
            description=product.description,
            ingredients=product.ingredients,
            nutrition=nutrition,
            badge=product.badge,
            image=product.image,
            hoverImage=product.hover_image,
            rating=product.rating,
            ratingsCount=product.ratings_count,
            reviews=reviews,
        )


# ==========================================================
# Product Create
# ==========================================================

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str
    price: float = Field(..., gt=0)
    original_price: Optional[float] = None
    weight: Optional[str] = None
    description: Optional[str] = None
    ingredients: Optional[str] = None
    nutrition: Optional[NutritionInfo] = None
    badge: Optional[str] = None
    image: Optional[str] = None
    hover_image: Optional[str] = None
    rating: float = 0.0
    ratings_count: int = 0
    sort_order: int = 0


# ==========================================================
# Product Update
# ==========================================================

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    weight: Optional[str] = None
    description: Optional[str] = None
    ingredients: Optional[str] = None
    nutrition: Optional[NutritionInfo] = None
    badge: Optional[str] = None
    image: Optional[str] = None
    hover_image: Optional[str] = None
    rating: Optional[float] = None
    ratings_count: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


# ==========================================================
# Paginated Product Response
# ==========================================================

class PaginatedProductResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
