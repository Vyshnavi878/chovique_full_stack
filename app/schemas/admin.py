from typing import Optional
from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_sales: float
    total_orders: int
    total_customers: int
    total_products: int
    low_stock_products_count: int
    pending_tickets_count: int


class UpdateOrderStatusPayload(BaseModel):
    status: str  # 'Processing', 'Shipped', 'Delivered', 'Cancelled'


# OfflineSale schemas

class OfflineSalePayload(BaseModel):
    product_name: str
    quantity: int
    total_price: float
    payment_method: str = "Cash"


class OfflineSaleResponse(BaseModel):
    id: str
    productName: str
    quantity: int
    totalPrice: float
    date: str
    paymentMethod: str


# Ticket resolve payload

class ResolveTicketPayload(BaseModel):
    admin_notes: Optional[str] = None


# Banner image upload response

class BannerImageResponse(BaseModel):
    image_url: str


class ImportSalesResponse(BaseModel):
    imported: int
    skipped: int
    message: str
