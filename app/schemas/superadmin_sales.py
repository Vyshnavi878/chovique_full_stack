from typing import List, Optional
from pydantic import BaseModel, Field


class SalesKPICard(BaseModel):
    """KPI metrics for Sales Analytics."""
    total_units_sold: int = Field(0, description="Total units sold across online and offline channels")
    total_units_prev: int = Field(0, description="Previous period total units sold")
    units_pct_change: float = Field(0.0, description="Percentage change in units sold")
    
    total_revenue: float = Field(0.0, description="Total combined revenue")
    total_revenue_prev: float = Field(0.0, description="Previous period total revenue")
    revenue_pct_change: float = Field(0.0, description="Percentage change in total revenue")
    
    online_revenue: float = Field(0.0, description="Online sales revenue")
    online_revenue_prev: float = Field(0.0, description="Previous period online revenue")
    online_pct_change: float = Field(0.0, description="Percentage change in online revenue")
    
    offline_revenue: float = Field(0.0, description="Offline sales revenue")
    offline_revenue_prev: float = Field(0.0, description="Previous period offline revenue")
    offline_pct_change: float = Field(0.0, description="Percentage change in offline revenue")
    
    top_selling_chocolate: Optional[str] = Field(None, description="Name of the top selling product")
    comparison_label: str = Field("vs last month", description="Comparison period label")


class ProductSalesPerformanceItem(BaseModel):
    """Product performance breakdown row."""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    category_name: str = Field("Chocolates", description="Category name")
    image_url: Optional[str] = Field(None, description="Product image thumbnail URL")
    price: float = Field(0.0, description="Current product price")
    online_units: int = Field(0, description="Units sold online")
    offline_units: int = Field(0, description="Units sold offline")
    total_units: int = Field(0, description="Total units sold")
    total_revenue: float = Field(0.0, description="Total revenue generated")
    stock_available: int = Field(0, description="Current available stock (read-only info)")


class ProductSalesPerformanceResponse(BaseModel):
    """Response for Product Sales Performance tab."""
    kpis: SalesKPICard
    products: List[ProductSalesPerformanceItem] = Field(default_factory=list)
    total: int = Field(0, description="Total matching products count")
    page: int = Field(1, description="Current page")
    limit: int = Field(10, description="Items per page")


class OnlineLedgerItem(BaseModel):
    """Single row in Online Sales Ledger."""
    id: str = Field(..., description="Order database ID")
    order_id: str = Field(..., description="Order display ID (e.g. ORD-1245)")
    created_at: str = Field(..., description="Formatted date string")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer email address")
    product_summary: str = Field(..., description="Items summary, e.g. Belgian Truffles x 2")
    quantity: int = Field(0, description="Total items in order")
    payment_method: str = Field("UPI", description="Payment method used")
    amount: float = Field(0.0, description="Total order amount")
    order_status: str = Field("Processing", description="Order fulfillment status")


class OnlineLedgerResponse(BaseModel):
    """Response for Online Sales Ledger tab."""
    items: List[OnlineLedgerItem] = Field(default_factory=list)
    total: int = Field(0, description="Total matching online orders count")
    page: int = Field(1, description="Current page")
    limit: int = Field(10, description="Items per page")


class OfflineLedgerItem(BaseModel):
    """Single row in Offline Sales Ledger."""
    id: str = Field(..., description="Offline sale database ID")
    receipt_id: str = Field(..., description="Receipt display ID (e.g. POS-8821)")
    created_at: str = Field(..., description="Formatted date string")
    product_name: str = Field(..., description="Product name")
    quantity: int = Field(1, description="Quantity sold")
    payment_method: str = Field("Cash", description="Payment method used")
    amount: float = Field(0.0, description="Total receipt amount")


class OfflineLedgerResponse(BaseModel):
    """Response for Offline Sales Ledger tab."""
    items: List[OfflineLedgerItem] = Field(default_factory=list)
    total: int = Field(0, description="Total matching offline sales count")
    page: int = Field(1, description="Current page")
    limit: int = Field(10, description="Items per page")
