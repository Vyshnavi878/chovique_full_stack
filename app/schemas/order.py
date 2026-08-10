from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.product import ProductResponse


class ShippingAddressSchema(BaseModel):
    name: str
    street: str
    city: str
    state: str
    zip: str
    phone: str


class OrderItemPayload(BaseModel):
    product_id: str
    quantity: int = 1


class OrderPayload(BaseModel):
    items: Optional[list[OrderItemPayload]] = []
    shipping_address: ShippingAddressSchema
    delivery_option: str = "Standard Delivery"
    payment_method: str = "UPI"
    coupon_code: Optional[str] = None
    coins_to_use: int = 0


class CartItemResponse(BaseModel):
    product: ProductResponse
    quantity: int


class OrderResponse(BaseModel):
    id: str
    items: list[CartItemResponse]
    total: float
    subtotal: float
    discount: float
    coupon_code: Optional[str] = None
    coupon_discount: float = 0.0
    coins_used: int = 0
    coin_discount: float = 0.0
    coins_earned: int = 0
    shipping: float
    tax: float = 0.0
    date: str
    status: str
    shippingAddress: ShippingAddressSchema
    deliveryOption: str
    paymentMethod: str
    invoice_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
