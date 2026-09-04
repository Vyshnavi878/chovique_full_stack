from typing import List, Optional
from pydantic import BaseModel, Field


class SalesMetricCard(BaseModel):
    """Card data with current value, previous comparison, and percentage change."""
    current_value: float = Field(0.0, description="Metric value for current period")
    previous_value: float = Field(0.0, description="Metric value for comparison period")
    percentage_change: float = Field(0.0, description="Percentage change (+/-)")
    comparison_label: str = Field("vs previous", description="Label for comparison period")


class SalesKPICard(BaseModel):
    """The 10 core Sales, Order & Stock KPI metrics (No revenue)."""
    total_orders: SalesMetricCard
    total_units_sold: SalesMetricCard
    online_orders: SalesMetricCard
    online_units_sold: SalesMetricCard
    offline_orders: SalesMetricCard
    offline_units_sold: SalesMetricCard
    pending_orders: SalesMetricCard
    cancelled_orders: SalesMetricCard
    current_stock: SalesMetricCard
    low_stock_products: SalesMetricCard


class SalesTrendPoint(BaseModel):
    """Daily/periodic time series point for Orders and Units Sold trend chart."""
    date: str = Field(..., description="Date label (e.g. '01 Sep')")
    total_orders: int = Field(0, description="Total placed orders in day")
    online_orders: int = Field(0, description="Online orders in day")
    offline_orders: int = Field(0, description="Offline POS sales in day")
    total_units: int = Field(0, description="Total item units sold in day")
    online_units: int = Field(0, description="Online item units sold in day")
    offline_units: int = Field(0, description="Offline item units sold in day")


class InventorySummary(BaseModel):
    """Catalog inventory snapshot."""
    current_stock: int = Field(0, description="Total stock available across all products")
    sold_quantity: int = Field(0, description="Total units sold in selected period")
    low_stock_count: int = Field(0, description="Number of products with stock <= 10 and > 0")
    out_of_stock_count: int = Field(0, description="Number of products with stock == 0")
    total_catalog_products: int = Field(0, description="Total active catalog products")


class ProductSalesPerformanceItem(BaseModel):
    """Product-wise sales performance table row."""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    category_name: str = Field("Chocolates", description="Category name")
    image_url: Optional[str] = Field(None, description="Product image thumbnail URL")
    price: float = Field(0.0, description="Current product price")
    units_sold: int = Field(0, description="Total units sold (Online + Offline)")
    online_units: int = Field(0, description="Units sold online")
    offline_units: int = Field(0, description="Units sold offline")
    current_stock: int = Field(0, description="Current available inventory stock")


class ProductSalesPerformanceResponse(BaseModel):
    """Complete response for Sales Analytics tab."""
    preset: str = Field("this_month", description="Selected date preset")
    date_from: str = Field(..., description="Start date ISO string")
    date_to: str = Field(..., description="End date ISO string")
    display_range: str = Field(..., description="Formatted display date range")
    kpis: SalesKPICard
    sales_trend: List[SalesTrendPoint] = Field(default_factory=list)
    inventory_summary: InventorySummary
    products: List[ProductSalesPerformanceItem] = Field(default_factory=list)
    total_products: int = Field(0, description="Total matching products count")
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
    payment_status: Optional[str] = Field("PENDING", description="Payment status")
    subtotal: Optional[float] = Field(0.0, description="Order subtotal")
    discount: Optional[float] = Field(0.0, description="Order discount")
    delivery_option: Optional[str] = Field("Standard Delivery", description="Shipping delivery option")
    shipping_address: Optional[dict] = Field(None, description="Customer shipping address")


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
    customer_name: Optional[str] = Field("Walk-in Customer", description="Customer or company name")
    phone: Optional[str] = Field("N/A", description="Customer contact phone")


class OfflineLedgerResponse(BaseModel):
    """Response for Offline Sales Ledger tab."""
    items: List[OfflineLedgerItem] = Field(default_factory=list)
    total: int = Field(0, description="Total matching offline sales count")
    page: int = Field(1, description="Current page")
    limit: int = Field(10, description="Items per page")
