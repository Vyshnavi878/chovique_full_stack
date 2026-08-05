from typing import Optional
from pydantic import BaseModel

from app.schemas.user import UserResponse
from app.schemas.order import OrderResponse
from app.schemas.ticket import SupportTicketResponse
class MonthlyRevenue(BaseModel):
    month: str          # e.g. "Jan 2025"
    online_revenue: float
    offline_revenue: float
    total: float


class TopProduct(BaseModel):
    name: str
    units_sold: int
    stock: int
    revenue: float


class DashboardStatsResponse(BaseModel):
    # Basic counts
    total_sales: float
    total_orders: int
    total_customers: int
    total_products: int
    low_stock_products_count: int
    pending_tickets_count: int
    # Extended KPI metrics
    total_units_sold: int
    total_inventory_stock: int
    total_online_revenue: float
    total_offline_revenue: float
    admin_count: int
    # Chart data
    monthly_revenue: list[MonthlyRevenue]
    top_products: list[TopProduct]


class AuditLogEntry(BaseModel):
    id: str
    action: str
    user_name: Optional[str]
    user_email: Optional[str]
    resource: Optional[str]
    details: Optional[str]
    created_at: str  # ISO format string


class CustomerDetailsResponse(BaseModel):
    user: UserResponse
    total_spent: float
    total_orders: int
    recent_orders: list[OrderResponse]
    support_tickets: list[SupportTicketResponse]


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


class CreateAdminRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: str = "admin"


class UpdateAdminPasswordPayload(BaseModel):
    password: str


class UpdateAdminRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None



# ======================================================
# CMS — Banners
# ======================================================

class CreateBannerRequest(BaseModel):
    title: str
    subtitle: Optional[str] = None
    tag: Optional[str] = None
    image: Optional[str] = None
    button_text: Optional[str] = None
    link: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


# ======================================================
# CMS — Testimonials
# ======================================================

class CreateTestimonialRequest(BaseModel):
    author: str
    title: Optional[str] = None
    text: str
    rating: float = 5.0
    initials: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


# ======================================================
# CMS — Instagram Reels
# ======================================================

class CreateReelRequest(BaseModel):
    video_url: Optional[str] = None
    likes: str = "0"
    comments: str = "0"
    views: str = "0 views"
    title: str
    sort_order: int = 0
    is_active: bool = True


class ReelResponse(BaseModel):
    id: str
    videoUrl: str
    likes: str
    comments: str
    views: str
    title: str


# ======================================================
# CMS — Site Config (Stats / Contact)
# ======================================================

class SetStatsRequest(BaseModel):
    happy_customers: int
    unique_flavors: int
    countries_shipped: int
    five_star_reviews_percent: int


class SetContactRequest(BaseModel):
    email: Optional[str] = "support@chovique.com"
    phone: Optional[str] = "+91 98765 43210"
    whatsapp: Optional[str] = "+91 98765 43210"
    support_hours: Optional[str] = "Mon - Sat: 10:00 AM - 8:00 PM | Sunday: 11:00 AM - 6:00 PM"
    address: Optional[str] = "42, MG Road, Indiranagar, Bangalore, Karnataka 560038"
    instagram: Optional[str] = "https://instagram.com"
    facebook: Optional[str] = "https://facebook.com"
    twitter: Optional[str] = "https://x.com"