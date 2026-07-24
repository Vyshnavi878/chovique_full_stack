from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.cart import AddToCartPayload, CartResponseSchema, UpdateCartQuantityPayload
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartResponseSchema, summary="Get current user's persistent cart")
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CartService(db)
    return await service.get_cart(current_user.id)


@router.post("", response_model=CartResponseSchema, summary="Add item to cart")
async def add_to_cart(
    payload: AddToCartPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = CartService(db)
        return await service.add_to_cart(current_user.id, payload.product_id, payload.quantity)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{product_id}", response_model=CartResponseSchema, summary="Update quantity of item in cart")
async def update_cart_quantity(
    product_id: str,
    payload: UpdateCartQuantityPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = CartService(db)
        return await service.update_quantity(current_user.id, product_id, payload.quantity)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{product_id}", response_model=CartResponseSchema, summary="Remove item from cart")
async def remove_from_cart(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CartService(db)
    return await service.remove_item(current_user.id, product_id)


@router.delete("", response_model=CartResponseSchema, summary="Clear full cart")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CartService(db)
    return await service.clear_cart(current_user.id)
