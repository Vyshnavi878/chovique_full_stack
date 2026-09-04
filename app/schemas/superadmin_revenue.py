from typing import List, Optional
from pydantic import BaseModel, Field


class KPICardWithComparison(BaseModel):
    """KPI metric with value and percentage comparison vs previous period."""
    current_value: float = Field(..., description="Current period value")
    previous_value: float = Field(..., description="Previous period value")
    percentage_change: float = Field(..., description="Percentage increase or decrease")
    comparison_label: str = Field(..., description="Label describing comparison, e.g. vs last month")


class RevenueTrendDataPoint(BaseModel):
    """Single data point in time series revenue & orders trend."""
    date: str = Field(..., description="Formatted date label, e.g. 1 Aug or 2026-08-01")
    total_revenue: float = Field(0.0, description="Total revenue collected for this interval")
    online_revenue: float = Field(0.0, description="Online sales revenue collected for this interval")
    cod_collected: float = Field(0.0, description="COD payments collected for this interval")
    pending_payment: float = Field(0.0, description="Pending payment amount for this interval")
    total_orders: int = Field(0, description="Total placed orders in this interval")
    paid_orders: int = Field(0, description="Paid orders count in this interval")
    cod_orders: int = Field(0, description="COD orders count in this interval")
    pending_orders: int = Field(0, description="Pending orders count in this interval")


class PaymentMethodRevenue(BaseModel):
    """Revenue breakdown by payment method."""
    method: str = Field(..., description="Payment method name, e.g. UPI, Card, Cash on Delivery")
    amount: float = Field(0.0, description="Total amount collected via this method")
    percentage: float = Field(0.0, description="Percentage of overall collected revenue")
    orders_count: int = Field(0, description="Number of orders via this payment method")


class TransactionOrderRow(BaseModel):
    """Single transaction row for the detailed orders table."""
    order_id: str = Field(..., description="Order ID")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field("", description="Customer email")
    customer_phone: str = Field("", description="Customer phone number")
    order_date: str = Field(..., description="Order placement timestamp (created_at)")
    payment_date: Optional[str] = Field(None, description="Actual payment received timestamp (paid_at)")
    amount: float = Field(0.0, description="Order total amount")
    payment_method: str = Field("UPI", description="Payment method used")
    payment_status: str = Field("PENDING", description="Payment status (PAID, PENDING, etc.)")
    order_status: str = Field("Processing", description="Order fulfillment status")


class RevenueSummaryRow(BaseModel):
    """Summary table row for a specific date/interval."""
    date: str = Field(..., description="Date formatted as YYYY-MM-DD or readable string")
    total_orders: int = Field(0, description="Total orders placed on this date")
    paid_orders: int = Field(0, description="Paid orders count on this date")
    cod_orders: int = Field(0, description="COD orders count on this date")
    pending_orders: int = Field(0, description="Pending orders count on this date")
    total_revenue: float = Field(0.0, description="Total revenue collected on this date")
    online_revenue: float = Field(0.0, description="Online revenue collected on this date")
    cod_collected: float = Field(0.0, description="COD revenue collected on this date")
    pending_payment: float = Field(0.0, description="Pending payment amount on this date")
    avg_order_value: float = Field(0.0, description="Average order value for interval")


class SuperadminRevenueResponse(BaseModel):
    """Complete Super Admin Revenue & Sales Analytics Response."""
    preset: str = Field(..., description="Active filter preset, e.g. today, yesterday, last_7_days, last_30_days, this_month, last_month, custom")
    date_basis: str = Field("order_date", description="Date filter basis: 'order_date' or 'payment_date'")
    date_from: str = Field(..., description="ISO start date string")
    date_to: str = Field(..., description="ISO end date string")
    display_range: str = Field(..., description="Readable date range string, e.g. 01 Aug 2026 - 31 Aug 2026")
    
    # 8 Primary KPI Cards
    total_revenue: KPICardWithComparison = Field(..., description="Total revenue actually collected")
    online_revenue: KPICardWithComparison = Field(..., description="Online order revenue collected")
    cod_collected: KPICardWithComparison = Field(..., description="COD payments collected")
    pending_payment: KPICardWithComparison = Field(..., description="Total amount in pending payment status")
    total_orders: KPICardWithComparison = Field(..., description="Total placed orders count")
    paid_orders: KPICardWithComparison = Field(..., description="Total paid orders count")
    cod_orders: KPICardWithComparison = Field(..., description="Total COD orders count (paid + pending)")
    pending_orders: KPICardWithComparison = Field(..., description="Total pending orders count")
    
    # Multi-Series Trend Chart
    revenue_trend: List[RevenueTrendDataPoint] = Field(default_factory=list, description="Time series trend data")
    
    # Payment Method Distributions
    revenue_by_payment_method: List[PaymentMethodRevenue] = Field(default_factory=list, description="Revenue by payment method breakdown")
    
    # Detailed Order Transactions Table
    transactions: List[TransactionOrderRow] = Field(default_factory=list, description="Detailed transaction rows for orders table")
    
    # Summary Table Rows
    summary_rows: List[RevenueSummaryRow] = Field(default_factory=list, description="Detailed summary rows for daily breakdown")
