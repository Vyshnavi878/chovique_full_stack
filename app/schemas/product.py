from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ==========================================================
# Nutrition Info
# ==========================================================

class NutritionInfo(BaseModel):
    servingSize: Optional[str] = ""
    calories: Optional[str] = ""
    totalFat: Optional[str] = ""
    saturatedFat: Optional[str] = ""
    transFat: Optional[str] = ""
    cholesterol: Optional[str] = ""
    sodium: Optional[str] = ""
    totalCarb: Optional[str] = ""
    dietaryFiber: Optional[str] = ""
    totalSugars: Optional[str] = ""
    addedSugars: Optional[str] = ""
    protein: Optional[str] = ""


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
    sku: Optional[str] = None
    name: str
    slug: str
    category: str
    price: float
    originalPrice: Optional[float] = None
    weight: Optional[str] = None
    stock: int = 100
    description: Optional[str] = None
    ingredients: Optional[str] = None
    nutrition: Optional[NutritionInfo] = None
    badge: Optional[str] = None
    image: Optional[str] = None
    hoverImage: Optional[str] = None
    rating: float = 0.0
    ratingsCount: int = 0
    isFeatured: bool = False
    isBestseller: bool = False
    isNewArrival: bool = False
    images: list[str] = []
    reviews: list[ReviewResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, product) -> "ProductResponse":
        """Convert an ORM Product to a frontend-compatible response."""

        nutrition = None
        if product.nutrition:
            nutrition = NutritionInfo(**product.nutrition)

        reviews = []
        if "reviews_list" in product.__dict__ and product.__dict__["reviews_list"]:
            reviews = [
                ReviewResponse(
                    id=r.id,
                    author=r.author,
                    rating=r.rating,
                    text=r.text,
                    date=r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
                    avatar=r.avatar,
                )
                for r in product.__dict__["reviews_list"]
            ]

        return cls(
            id=product.id,
            sku=getattr(product, "sku", None),
            name=product.name,
            slug=product.slug,
            category=product.category,
            price=product.price,
            originalPrice=product.original_price,
            weight=product.weight,
            stock=getattr(product, "stock", 100),
            description=product.description,
            ingredients=product.ingredients,
            nutrition=nutrition,
            badge=product.badge,
            image=product.image,
            hoverImage=product.hover_image,
            rating=product.rating,
            ratingsCount=product.ratings_count,
            isFeatured=getattr(product, "is_featured", False),
            isBestseller=getattr(product, "is_bestseller", False),
            isNewArrival=getattr(product, "is_new_arrival", False),
            images=getattr(product, "images", []) or [],
            reviews=reviews,
        )


# ==========================================================
# Product Create
# ==========================================================

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: Optional[str] = None
    category: str
    price: float = Field(..., gt=0)
    original_price: Optional[float] = None
    weight: Optional[str] = None
    stock: int = 100
    description: Optional[str] = None
    ingredients: Optional[str] = None
    nutrition: Optional[NutritionInfo] = None
    badge: Optional[str] = None
    image: Optional[str] = None
    hover_image: Optional[str] = None
    rating: float = 0.0
    ratings_count: int = 0
    sort_order: int = 0
    is_featured: bool = False
    is_bestseller: bool = False
    is_new_arrival: bool = False
    images: list[str] = []



# ==========================================================
# Product Update
# ==========================================================

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    weight: Optional[str] = None
    stock: Optional[int] = None
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
    is_featured: Optional[bool] = None
    is_bestseller: Optional[bool] = None
    is_new_arrival: Optional[bool] = None
    images: Optional[list[str]] = None



# ==========================================================
# Paginated Product Response
# ==========================================================

class PaginatedProductResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
