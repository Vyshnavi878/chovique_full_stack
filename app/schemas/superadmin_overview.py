from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class KPICardData(BaseModel):
    current_value: float
    previous_value: float
    percentage_change: float
    comparison_label: str

    model_config = ConfigDict(from_attributes=True)


class RevenueTrendPoint(BaseModel):
    date: str
    revenue: float

    model_config = ConfigDict(from_attributes=True)


class SalesSourceData(BaseModel):
    online_revenue: float
    online_percentage: float
    offline_revenue: float
    offline_percentage: float

    model_config = ConfigDict(from_attributes=True)


class TopSellingProductOverview(BaseModel):
    id: str
    name: str
    image_url: Optional[str] = None
    units_sold: int
    revenue: float

    model_config = ConfigDict(from_attributes=True)


class RecentActivityItem(BaseModel):
    id: str
    action: str
    description: str
    timestamp: str
    user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SuperadminOverviewResponse(BaseModel):
    total_revenue: KPICardData
    total_orders: KPICardData
    total_customers: KPICardData
    active_admins: KPICardData
    revenue_trend: List[RevenueTrendPoint]
    sales_source: SalesSourceData
    top_selling_products: List[TopSellingProductOverview]
    recent_activities: List[RecentActivityItem]

    model_config = ConfigDict(from_attributes=True)
