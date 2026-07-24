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
    items: list[OrderItemPayload]
    shipping_address: ShippingAddressSchema
    delivery_option: str = "Standard Delivery"
    payment_method: str = "UPI"
    coupon_code: Optional[str] = None


class CartItemResponse(BaseModel):
    product: ProductResponse
    quantity: int


class OrderResponse(BaseModel):
    id: str
    items: list[CartItemResponse]
    total: float
    subtotal: float
    discount: float
    shipping: float
    date: str
    status: str
    shippingAddress: ShippingAddressSchema
    deliveryOption: str
    paymentMethod: str

    model_config = ConfigDict(from_attributes=True)
