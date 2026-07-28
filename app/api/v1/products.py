from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.product import (
    PaginatedProductResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


# ======================================================
# LIST PRODUCTS (Public)
# ======================================================

@router.get(
    "",
    response_model=PaginatedProductResponse,
    summary="List products with pagination, filtering, and sorting",
)
async def list_products(
    search: Optional[str] = Query(default=None, description="Search by name or description"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    price_min: Optional[float] = Query(default=None, ge=0, description="Minimum price"),
    price_max: Optional[float] = Query(default=None, ge=0, description="Maximum price"),
    min_rating: Optional[float] = Query(default=None, ge=0, le=5, description="Minimum rating"),
    sort: Optional[str] = Query(default=None, description="Sort: price_asc, price_desc, rating, newest, name_asc, name_desc"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=12, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)

    return await service.list_products(
        search=search,
        category=category,
        price_min=price_min,
        price_max=price_max,
        min_rating=min_rating,
        sort=sort,
        page=page,
        per_page=per_page,
    )


# ======================================================
# GET SINGLE PRODUCT (Public)
# ======================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a single product by ID",
)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.get_product(product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return product


# ======================================================
# CREATE PRODUCT (Admin only)
# Accepts multipart/form-data matching frontend FormData
# ======================================================

import json as _json
from fastapi import Form, UploadFile, File
import os as _os
import uuid as _uuid

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product (admin only)",
)
async def create_product(
    name: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    original_price: Optional[float] = Form(default=None),
    weight: Optional[str] = Form(default=None),
    stock: Optional[int] = Form(default=10),
    description: Optional[str] = Form(default=None),
    ingredients: Optional[str] = Form(default=None),
    badge: Optional[str] = Form(default=None),
    sort_order: int = Form(default=0),
    # Nutrition fields as individual form fields
    nutrition_calories: Optional[str] = Form(default=None),
    nutrition_total_fat: Optional[str] = Form(default=None),
    nutrition_saturated_fat: Optional[str] = Form(default=None),
    nutrition_cholesterol: Optional[str] = Form(default=None),
    nutrition_sodium: Optional[str] = Form(default=None),
    nutrition_total_carb: Optional[str] = Form(default=None),
    nutrition_protein: Optional[str] = Form(default=None),
    image: Optional[UploadFile] = File(default=None),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.product import NutritionInfo as _NutritionInfo

    # Clean category & badge enums
    valid_categories = ["dark", "milk", "white", "gift", "beverage"]
    clean_cat = category.lower().strip() if (category and category.lower().strip() in valid_categories) else "dark"

    valid_badges = ["Bestseller", "New", "Premium", "Limited"]
    clean_badge = badge if (badge and badge in valid_badges) else None

    from app.integrations.cloudinary import cloudinary_service

    # Handle image upload
    image_url: Optional[str] = None
    if image and hasattr(image, "filename") and image.filename:
        try:
            content = await image.read()
            if content:
                image_url = await cloudinary_service.upload_image(
                    file_bytes=content,
                    filename=image.filename,
                    folder="products",
                )
        except Exception as err:
            logger.warning("Failed to upload product image file: %s", err)


    if not image_url:
        image_url = "https://images.unsplash.com/photo-1548907040-4d42b52115ca?auto=format&fit=crop&w=600&q=80"

    nutrition = None
    if any([nutrition_calories, nutrition_total_fat, nutrition_saturated_fat,
            nutrition_cholesterol, nutrition_sodium, nutrition_total_carb, nutrition_protein]):
        nutrition = _NutritionInfo(
            calories=nutrition_calories or "",
            totalFat=nutrition_total_fat or "",
            saturatedFat=nutrition_saturated_fat or "",
            cholesterol=nutrition_cholesterol or "",
            sodium=nutrition_sodium or "",
            totalCarb=nutrition_total_carb or "",
            protein=nutrition_protein or "",
        )

    data = ProductCreate(
        name=name,
        category=clean_cat,
        price=price,
        original_price=original_price,
        weight=weight,
        stock=stock if stock is not None else 10,
        description=description,
        ingredients=ingredients,
        nutrition=nutrition,
        badge=clean_badge,
        image=image_url,
        sort_order=sort_order,
    )

    service = ProductService(db)
    return await service.create_product(data)



# ======================================================
# UPDATE PRODUCT (Admin only)
# ======================================================

@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product (admin only)",
)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    product = await service.update_product(product_id, data)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return product


# ======================================================
# DELETE PRODUCT (Admin only)
# ======================================================

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product (admin only)",
)
async def delete_product(
    product_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = ProductService(db)
    deleted = await service.delete_product(product_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )


# ======================================================
# PRODUCT REVIEWS (Public / Customer)
# ======================================================

from app.schemas.product import ReviewResponse
from app.services.customer_service import CustomerService
from pydantic import BaseModel, Field

class CreateReviewRequest(BaseModel):
    author: str
    rating: float = Field(..., ge=1, le=5)
    text: str

@router.get(
    "/{product_id}/reviews",
    response_model=list[ReviewResponse],
    summary="Get reviews for a product",
)
async def get_product_reviews(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.get_product_reviews(product_id)

@router.post(
    "/{product_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a review for a product",
)
async def create_product_review(
    product_id: str,
    payload: CreateReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.create_product_review(
        product_id=product_id,
        author=payload.author,
        rating=payload.rating,
        text=payload.text,
    )
