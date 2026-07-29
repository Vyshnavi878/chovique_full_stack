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


class CreateAdminRequest(BaseModel):
    full_name: str
    email: str
    password: str
    scope: Optional[str] = "All Boutiques"


class UpdateAdminPasswordPayload(BaseModel):
    password: str



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
    email: str
    phone: str
    address: str
    instagram: str
    facebook: str
    twitter: str