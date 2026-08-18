import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.offline_sale import OfflineSale
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.superadmin_sales import (
    OfflineLedgerItem,
    OfflineLedgerResponse,
    OnlineLedgerItem,
    OnlineLedgerResponse,
    ProductSalesPerformanceItem,
    ProductSalesPerformanceResponse,
    SalesKPICard,
)


class SuperadminSalesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _calc_pct_change(self, current: float, previous: float) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    async def get_sales_kpis(self) -> SalesKPICard:
        """Calculate overall sales KPI metrics comparing current month vs last month."""
        now = datetime.now(timezone.utc)
        curr_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)

        if now.month == 1:
            prev_start = datetime(now.year - 1, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
            prev_end = curr_start - timedelta(seconds=1)
        else:
            prev_start = datetime(now.year, now.month - 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            prev_end = curr_start - timedelta(seconds=1)

        valid_statuses = ["Paid", "Delivered", "Shipped", "Processing"]

        # -------------------------------------------------------------------
        # IMPORTANT: Revenue and Units must be computed in SEPARATE queries.
        #
        # If we JOIN Order with OrderItem in a single query and SUM Order.total,
        # the order total gets counted once per item row — causing it to be
        # doubled (or tripled, etc.) for multi-item orders.
        #
        # Correct approach:
        #   - Revenue  → query Order directly (no OrderItem join)
        #   - Units    → query OrderItem with the Order join
        # -------------------------------------------------------------------

        # Current period: online REVENUE (query Order directly — no join)
        online_curr_rev_res = await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0.0))
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.payment_status) == "PAID",
            )
        )
        online_curr_rev = online_curr_rev_res.scalar_one() or 0.0

        # Current period: online UNITS (requires OrderItem join)
        online_curr_units_res = await self.db.execute(
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.payment_status) == "PAID",
            )
        )
        online_curr_units = online_curr_units_res.scalar_one() or 0

        # Current period offline
        offline_curr_res = await self.db.execute(
            select(
                func.coalesce(func.sum(OfflineSale.quantity), 0),
                func.coalesce(func.sum(OfflineSale.total_price), 0.0),
            ).where(
                OfflineSale.created_at >= curr_start,
                OfflineSale.created_at <= curr_end,
            )
        )
        offline_curr_units, offline_curr_rev = offline_curr_res.one()

        # Previous period: online REVENUE (query Order directly — no join)
        online_prev_rev_res = await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0.0))
            .where(
                Order.created_at >= prev_start,
                Order.created_at <= prev_end,
                func.upper(Order.payment_status) == "PAID",
            )
        )
        online_prev_rev = online_prev_rev_res.scalar_one() or 0.0

        # Previous period: online UNITS (requires OrderItem join)
        online_prev_units_res = await self.db.execute(
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.created_at >= prev_start,
                Order.created_at <= prev_end,
                func.upper(Order.payment_status) == "PAID",
            )
        )
        online_prev_units = online_prev_units_res.scalar_one() or 0

        # Previous period offline
        offline_prev_res = await self.db.execute(
            select(
                func.coalesce(func.sum(OfflineSale.quantity), 0),
                func.coalesce(func.sum(OfflineSale.total_price), 0.0),
            ).where(
                OfflineSale.created_at >= prev_start,
                OfflineSale.created_at <= prev_end,
            )
        )
        offline_prev_units, offline_prev_rev = offline_prev_res.one()

        total_curr_units = int(online_curr_units + offline_curr_units)
        total_prev_units = int(online_prev_units + offline_prev_units)

        total_curr_rev = float(online_curr_rev + offline_curr_rev)
        total_prev_rev = float(online_prev_rev + offline_prev_rev)

        # Top selling chocolate
        top_prod_res = await self.db.execute(
            select(Product.name, func.sum(OrderItem.quantity).label("units"))
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(func.upper(Order.payment_status) == "PAID")
            .group_by(Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(1)
        )
        top_prod_row = top_prod_res.first()
        top_chocolate = top_prod_row[0] if top_prod_row else "Belgian Dark Truffle Bar"

        return SalesKPICard(
            total_units_sold=total_curr_units,
            total_units_prev=total_prev_units,
            units_pct_change=self._calc_pct_change(total_curr_units, total_prev_units),
            total_revenue=round(total_curr_rev, 2),
            total_revenue_prev=round(total_prev_rev, 2),
            revenue_pct_change=self._calc_pct_change(total_curr_rev, total_prev_rev),
            online_revenue=round(float(online_curr_rev), 2),
            online_revenue_prev=round(float(online_prev_rev), 2),
            online_pct_change=self._calc_pct_change(online_curr_rev, online_prev_rev),
            offline_revenue=round(float(offline_curr_rev), 2),
            offline_revenue_prev=round(float(offline_prev_rev), 2),
            offline_pct_change=self._calc_pct_change(offline_curr_rev, offline_prev_rev),
            top_selling_chocolate=top_chocolate,
            comparison_label="vs last month",
        )

    async def get_product_sales_performance(
        self,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        limit: int = 10,
    ) -> ProductSalesPerformanceResponse:
        """Fetch aggregated product performance table and KPI metrics."""
        kpis = await self.get_sales_kpis()

        # Query all products
        stmt = select(Product)
        if search:
            stmt = stmt.where(Product.name.ilike(f"%{search}%"))

        products_res = await self.db.execute(stmt)
        products = products_res.scalars().all()

        valid_statuses = ["Paid", "Delivered", "Shipped", "Processing"]

        # Fetch online units & revenue per product
        online_stmt = (
            select(
                OrderItem.product_id,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
                func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0.0).label("revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(func.upper(Order.payment_status) == "PAID")
        )
        if date_from:
            online_stmt = online_stmt.where(Order.created_at >= date_from)
        if date_to:
            online_stmt = online_stmt.where(Order.created_at <= date_to)
        online_stmt = online_stmt.group_by(OrderItem.product_id)

        online_data_res = await self.db.execute(online_stmt)
        online_map = {p_id: (int(u), float(r)) for p_id, u, r in online_data_res.all()}

        # Fetch offline sales per product name
        offline_stmt = select(
            OfflineSale.product_name,
            func.coalesce(func.sum(OfflineSale.quantity), 0).label("units"),
            func.coalesce(func.sum(OfflineSale.total_price), 0.0).label("revenue"),
        )
        if date_from:
            offline_stmt = offline_stmt.where(OfflineSale.created_at >= date_from)
        if date_to:
            offline_stmt = offline_stmt.where(OfflineSale.created_at <= date_to)
        offline_stmt = offline_stmt.group_by(OfflineSale.product_name)

        offline_data_res = await self.db.execute(offline_stmt)
        offline_map = {name.lower(): (int(u), float(r)) for name, u, r in offline_data_res.all()}

        performance_items: List[ProductSalesPerformanceItem] = []

        for prod in products:
            on_units, on_rev = online_map.get(prod.id, (0, 0.0))
            off_units, off_rev = offline_map.get(prod.name.lower(), (0, 0.0))

            tot_units = on_units + off_units
            tot_rev = round(on_rev + off_rev, 2)

            cat_name = str(prod.category).title() if prod.category else "Chocolates"

            performance_items.append(
                ProductSalesPerformanceItem(
                    id=prod.id,
                    name=prod.name,
                    category_name=cat_name,
                    image_url=prod.image,
                    price=float(prod.price),
                    online_units=on_units,
                    offline_units=off_units,
                    total_units=tot_units,
                    total_revenue=tot_rev,
                    stock_available=int(prod.stock if prod.stock is not None else 0),
                )
            )

        # Sort by total revenue descending
        performance_items.sort(key=lambda x: x.total_revenue, reverse=True)

        total_count = len(performance_items)
        offset = (page - 1) * limit
        paginated_items = performance_items[offset : offset + limit]

        return ProductSalesPerformanceResponse(
            kpis=kpis,
            products=paginated_items,
            total=total_count,
            page=page,
            limit=limit,
        )

    async def get_online_sales_ledger(
        self,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        payment_method: Optional[str] = None,
        payment_status_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        limit: int = 10,
    ) -> OnlineLedgerResponse:
        """Fetch paginated online sales ledger from orders table."""
        stmt = select(Order).options(selectinload(Order.user), selectinload(Order.items))

        if search:
            stmt = stmt.join(User, Order.user_id == User.id, isouter=True).where(
                or_(
                    Order.id.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )

        if status_filter and status_filter.upper() != "ALL":
            stmt = stmt.where(Order.status == status_filter)

        if payment_method and payment_method.upper() != "ALL":
            stmt = stmt.where(Order.payment_method.ilike(f"%{payment_method}%"))

        if payment_status_filter:
            psf = payment_status_filter.lower()
            if psf == "completed":
                stmt = stmt.where(func.upper(Order.payment_status) == "PAID")
            elif psf == "pending":
                stmt = stmt.where(func.upper(Order.payment_status).in_(["PENDING", "PROCESSING"]))
            elif psf in ["cancelled", "failed"]:
                stmt = stmt.where(func.upper(Order.payment_status).in_(["FAILED", "CANCELLED", "REFUNDED", "REFUND PENDING", "PARTIALLY REFUNDED"]))
            else:
                stmt = stmt.where(func.upper(Order.payment_status) == psf.upper())

        if date_from:
            stmt = stmt.where(Order.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Order.created_at <= date_to)

        # Count total matching orders
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.db.execute(count_stmt)
        total_count = total_res.scalar_one() or 0

        # Paginated results
        stmt = stmt.order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit)
        orders_res = await self.db.execute(stmt)
        orders = orders_res.scalars().all()

        items: List[OnlineLedgerItem] = []
        for ord_obj in orders:
            cust_name = ord_obj.user.full_name if ord_obj.user else "Guest Customer"
            cust_email = ord_obj.user.email if ord_obj.user else "N/A"

            # Create product summary string
            prod_names = []
            tot_qty = 0
            if ord_obj.items:
                for itm in ord_obj.items:
                    tot_qty += itm.quantity
                    p_name = itm.product.name if itm.product else "Chocolate Item"
                    prod_names.append(f"{p_name} (x{itm.quantity})")
            
            prod_summary = ", ".join(prod_names) if prod_names else "Luxury Chocolates"

            display_ord_id = f"ORD-{ord_obj.id[:8].upper()}" if len(ord_obj.id) > 12 else ord_obj.id

            items.append(
                OnlineLedgerItem(
                    id=ord_obj.id,
                    order_id=display_ord_id,
                    created_at=ord_obj.created_at.strftime("%d %b %Y, %I:%M %p"),
                    customer_name=cust_name,
                    customer_email=cust_email,
                    product_summary=prod_summary,
                    quantity=tot_qty if tot_qty > 0 else 1,
                    payment_method=ord_obj.payment_method or "UPI",
                    amount=round(float(ord_obj.total), 2),
                    order_status=ord_obj.status or "Processing",
                )
            )

        return OnlineLedgerResponse(
            items=items,
            total=total_count,
            page=page,
            limit=limit,
        )

    async def get_offline_sales_ledger(
        self,
        search: Optional[str] = None,
        payment_method: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        limit: int = 10,
    ) -> OfflineLedgerResponse:
        """Fetch paginated offline sales ledger from offline_sales table."""
        stmt = select(OfflineSale)

        if search:
            stmt = stmt.where(
                or_(
                    OfflineSale.id.ilike(f"%{search}%"),
                    OfflineSale.product_name.ilike(f"%{search}%"),
                )
            )

        if payment_method and payment_method.upper() != "ALL":
            stmt = stmt.where(OfflineSale.payment_method.ilike(f"%{payment_method}%"))

        if date_from:
            stmt = stmt.where(OfflineSale.created_at >= date_from)
        if date_to:
            stmt = stmt.where(OfflineSale.created_at <= date_to)

        # Count total matching offline sales
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.db.execute(count_stmt)
        total_count = total_res.scalar_one() or 0

        # Paginated results
        stmt = stmt.order_by(OfflineSale.created_at.desc()).offset((page - 1) * limit).limit(limit)
        sales_res = await self.db.execute(stmt)
        sales = sales_res.scalars().all()

        items: List[OfflineLedgerItem] = []
        for sale in sales:
            display_receipt_id = f"POS-{sale.id[:8].upper()}"

            items.append(
                OfflineLedgerItem(
                    id=sale.id,
                    receipt_id=display_receipt_id,
                    created_at=sale.created_at.strftime("%d %b %Y, %I:%M %p"),
                    product_name=sale.product_name,
                    quantity=sale.quantity,
                    payment_method=sale.payment_method or "Cash",
                    amount=round(float(sale.total_price), 2),
                )
            )

        return OfflineLedgerResponse(
            items=items,
            total=total_count,
            page=page,
            limit=limit,
        )

    async def generate_sales_csv(
        self,
        tab: str = "products",
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Generates CSV report based on active tab view."""
        output = io.StringIO()
        writer = csv.writer(output)

        if tab == "online":
            ledger = await self.get_online_sales_ledger(search=search, date_from=date_from, date_to=date_to, page=1, limit=1000)
            writer.writerow(["CHOVIQUE ONLINE SALES LEDGER"])
            writer.writerow(["Order ID", "Date", "Customer Name", "Customer Email", "Products Purchased", "Quantity", "Payment Method", "Amount (INR)", "Order Status"])
            for item in ledger.items:
                writer.writerow([
                    item.order_id,
                    item.created_at,
                    item.customer_name,
                    item.customer_email,
                    item.product_summary,
                    item.quantity,
                    item.payment_method,
                    item.amount,
                    item.order_status,
                ])

        elif tab == "offline":
            ledger = await self.get_offline_sales_ledger(search=search, date_from=date_from, date_to=date_to, page=1, limit=1000)
            writer.writerow(["CHOVIQUE OFFLINE BOUTIQUE SALES LEDGER"])
            writer.writerow(["Receipt ID", "Date", "Product Name", "Quantity", "Payment Method", "Amount (INR)"])
            for item in ledger.items:
                writer.writerow([
                    item.receipt_id,
                    item.created_at,
                    item.product_name,
                    item.quantity,
                    item.payment_method,
                    item.amount,
                ])

        else:
            # Products tab (Default)
            perf = await self.get_product_sales_performance(search=search, date_from=date_from, date_to=date_to, page=1, limit=1000)
            writer.writerow(["CHOVIQUE PRODUCT SALES & STOCK PERFORMANCE REPORT"])
            writer.writerow(["Product Name", "Category", "Price (INR)", "Online Units", "Offline Units", "Total Units Sold", "Total Revenue (INR)", "Stock Available"])
            for item in perf.products:
                writer.writerow([
                    item.name,
                    item.category_name,
                    item.price,
                    item.online_units,
                    item.offline_units,
                    item.total_units,
                    item.total_revenue,
                    item.stock_available,
                ])

        return output.getvalue()
