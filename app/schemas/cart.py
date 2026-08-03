from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.product import ProductResponse


class AddToCartPayload(BaseModel):
    product_id: str
    quantity: int = 1


class UpdateCartQuantityPayload(BaseModel):
    quantity: int


class CartItemResponseSchema(BaseModel):
    id: str
    product: ProductResponse
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class CartResponseSchema(BaseModel):
    id: str
    items: list[CartItemResponseSchema] = []
    subtotal: float = 0.0
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SyncCartItem(BaseModel):
    product_id: str
    quantity: int


class SyncCartPayload(BaseModel):
    items: list[SyncCartItem]
