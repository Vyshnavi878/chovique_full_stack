from typing import List, Optional
from pydantic import BaseModel, Field


class KPICardWithComparison(BaseModel):
    """KPI metric with value and percentage comparison vs previous period."""
    current_value: float = Field(..., description="Current period value")
    previous_value: float = Field(..., description="Previous period value")
    percentage_change: float = Field(..., description="Percentage increase or decrease")
    comparison_label: str = Field(..., description="Label describing comparison, e.g. vs last month")


class RevenueTrendDataPoint(BaseModel):
    """Single data point in time series revenue trend."""
    date: str = Field(..., description="Formatted date label, e.g. 1 Aug or 2026-08-01")
    online_revenue: float = Field(0.0, description="Online sales revenue for this interval")
    offline_revenue: float = Field(0.0, description="Offline sales revenue for this interval")
    total_revenue: float = Field(0.0, description="Total combined revenue for this interval")


class RevenueBySource(BaseModel):
    """Breakdown of revenue by sales channel (Online vs Offline)."""
    online_revenue: float = Field(0.0, description="Total online revenue")
    online_percentage: float = Field(0.0, description="Online revenue percentage")
    offline_revenue: float = Field(0.0, description="Total offline revenue")
    offline_percentage: float = Field(0.0, description="Offline revenue percentage")


class PaymentMethodRevenue(BaseModel):
    """Revenue breakdown by payment method."""
    method: str = Field(..., description="Payment method name, e.g. UPI, Card, Cash on Delivery")
    amount: float = Field(0.0, description="Total amount collected via this method")
    percentage: float = Field(0.0, description="Percentage of overall revenue")


class RevenueSummaryRow(BaseModel):
    """Summary table row for a specific date/interval."""
    date: str = Field(..., description="Date formatted as YYYY-MM-DD or readable string")
    online_orders: int = Field(0, description="Number of online orders completed")
    online_revenue: float = Field(0.0, description="Online revenue collected")
    offline_sales: int = Field(0, description="Number of offline sales registered")
    offline_revenue: float = Field(0.0, description="Offline revenue collected")
    total_revenue: float = Field(0.0, description="Total revenue for interval")
    avg_order_value: float = Field(0.0, description="Average order value for interval")


class SuperadminRevenueResponse(BaseModel):
    """Complete Super Admin Revenue Analytics Response."""
    preset: str = Field(..., description="Active filter preset, e.g. today, week, month, 3months, year, custom")
    date_from: str = Field(..., description="ISO start date string")
    date_to: str = Field(..., description="ISO end date string")
    display_range: str = Field(..., description="Readable date range string, e.g. 01 Aug 2026 - 31 Aug 2026")
    
    # 4 Primary KPI Cards
    total_income: KPICardWithComparison = Field(..., description="Total income (Online + Offline)")
    online_revenue: KPICardWithComparison = Field(..., description="Online order revenue")
    offline_revenue: KPICardWithComparison = Field(..., description="Offline store revenue")
    avg_order_value: KPICardWithComparison = Field(..., description="Average order value")
    
    # Trend Chart
    revenue_trend: List[RevenueTrendDataPoint] = Field(default_factory=list, description="Time series trend data")
    
    # Distributions
    revenue_by_source: RevenueBySource = Field(..., description="Revenue by source distribution")
    revenue_by_payment_method: List[PaymentMethodRevenue] = Field(default_factory=list, description="Revenue by payment method breakdown")
    
    # Detailed Summary Table
    summary_rows: List[RevenueSummaryRow] = Field(default_factory=list, description="Detailed summary rows for datatable")
