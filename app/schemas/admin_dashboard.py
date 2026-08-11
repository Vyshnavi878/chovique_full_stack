from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, model_validator


# ==========================================================
# Date Filter Query Validator
# ==========================================================

class DateFilterQuery(BaseModel):
    preset: Optional[str] = None  # today, 7days, 30days, month, custom
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode='after')
    def validate_range(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("Start date cannot be after end date.")
        return self


# ==========================================================
# Endpoint Response Schemas
# ==========================================================

class DashboardSummaryResponse(BaseModel):
    total_revenue: float
    total_orders: int
    total_customers: int
    reward_coins_issued: int
    revenue_change_percent: float = 12.5
    orders_change_percent: float = 8.2
    customers_change_percent: float = 6.7
    coins_change_percent: float = 13.3


class RevenueStatsResponse(BaseModel):
    total_revenue: float
    online_revenue: float
    offline_revenue: float
    average_order_value: float


class OrderStatusCount(BaseModel):
    status: str
    count: int


class OrderStatsResponse(BaseModel):
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    status_breakdown: list[OrderStatusCount]


class CustomerStatsResponse(BaseModel):
    total_customers: int
    new_customers_in_period: int
    active_customers_in_period: int


class RewardCoinStatsResponse(BaseModel):
    total_coins_issued: int
    total_coins_earned: int
    total_coins_redeemed: int
    active_wallet_holders: int


class SalesChartPoint(BaseModel):
    date: str
    sales: float
    orders_count: int = 0


class SalesChartResponse(BaseModel):
    timeframe: str
    points: list[SalesChartPoint]


class TopSellingProductItem(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    weight: Optional[str] = None
    price: float
    units_sold: int
    total_revenue: float


class TopSellingProductsResponse(BaseModel):
    products: list[TopSellingProductItem]


class RecentOrderItem(BaseModel):
    id: str
    customer_name: str
    customer_email: Optional[str] = None
    amount: float
    status: str
    payment_status: str
    created_at: str


class RecentOrdersResponse(BaseModel):
    orders: list[RecentOrderItem]


class LowStockProductItem(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    category: str
    price: float
    stock: int


class LowStockProductsResponse(BaseModel):
    low_stock_count: int
    threshold: int
    products: list[LowStockProductItem]
