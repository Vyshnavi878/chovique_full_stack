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
    InventorySummary,
    OfflineLedgerItem,
    OfflineLedgerResponse,
    OnlineLedgerItem,
    OnlineLedgerResponse,
    ProductSalesPerformanceItem,
    ProductSalesPerformanceResponse,
    SalesKPICard,
    SalesMetricCard,
    SalesTrendPoint,
)


class SuperadminSalesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _calc_pct_change(self, current: float, previous: float) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    def _resolve_date_range(
        self,
        preset: str = "this_month",
        date_from_iso: Optional[str] = None,
        date_to_iso: Optional[str] = None,
    ) -> Tuple[datetime, datetime, datetime, datetime, str, str, str, str]:
        """
        Resolves current and previous date boundaries in IST/UTC.
        Returns (curr_start, curr_end, prev_start, prev_end, display_range, from_str, to_str, comp_label).
        """
        try:
            from zoneinfo import ZoneInfo
            tz_ist = ZoneInfo("Asia/Kolkata")
        except Exception:
            from dateutil.tz import gettz
            tz_ist = gettz("Asia/Kolkata") or timezone.utc

        now_ist = datetime.now(tz_ist)
        today_start_ist = datetime(now_ist.year, now_ist.month, now_ist.day, 0, 0, 0, tzinfo=tz_ist)
        today_end_ist = datetime(now_ist.year, now_ist.month, now_ist.day, 23, 59, 59, tzinfo=tz_ist)

        clean_preset = (preset or "this_month").lower().strip()

        if clean_preset == "today":
            c_start = today_start_ist
            c_end = today_end_ist
            p_start = today_start_ist - timedelta(days=1)
            p_end = today_start_ist - timedelta(seconds=1)
            display_range = c_start.strftime("%d %b %Y")
            comp_label = "vs yesterday"

        elif clean_preset == "yesterday":
            c_start = today_start_ist - timedelta(days=1)
            c_end = today_start_ist - timedelta(seconds=1)
            p_start = c_start - timedelta(days=1)
            p_end = c_start - timedelta(seconds=1)
            display_range = c_start.strftime("%d %b %Y")
            comp_label = "vs day before"

        elif clean_preset == "last_7_days":
            c_start = today_start_ist - timedelta(days=6)
            c_end = today_end_ist
            p_start = c_start - timedelta(days=7)
            p_end = c_start - timedelta(seconds=1)
            display_range = f"{c_start.strftime('%d %b')} - {c_end.strftime('%d %b %Y')}"
            comp_label = "vs previous 7 days"

        elif clean_preset == "last_30_days":
            c_start = today_start_ist - timedelta(days=29)
            c_end = today_end_ist
            p_start = c_start - timedelta(days=30)
            p_end = c_start - timedelta(seconds=1)
            display_range = f"{c_start.strftime('%d %b')} - {c_end.strftime('%d %b %Y')}"
            comp_label = "vs previous 30 days"

        elif clean_preset == "last_month":
            if now_ist.month == 1:
                lm_start = datetime(now_ist.year - 1, 12, 1, 0, 0, 0, tzinfo=tz_ist)
            else:
                lm_start = datetime(now_ist.year, now_ist.month - 1, 1, 0, 0, 0, tzinfo=tz_ist)
            c_start = lm_start
            c_end = today_start_ist.replace(day=1) - timedelta(seconds=1)

            if lm_start.month == 1:
                p_start = datetime(lm_start.year - 1, 12, 1, 0, 0, 0, tzinfo=tz_ist)
            else:
                p_start = datetime(lm_start.year, lm_start.month - 1, 1, 0, 0, 0, tzinfo=tz_ist)
            p_end = c_start - timedelta(seconds=1)

            display_range = f"{c_start.strftime('%d %b')} - {c_end.strftime('%d %b %Y')}"
            comp_label = "vs month before"

        elif clean_preset == "all_time":
            c_start = datetime(2020, 1, 1, 0, 0, 0, tzinfo=tz_ist)
            c_end = today_end_ist + timedelta(days=365)
            p_start = c_start
            p_end = c_end
            display_range = "All Time"
            comp_label = "all time"

        elif clean_preset == "custom" and date_from_iso and date_to_iso:
            try:
                df = datetime.fromisoformat(date_from_iso.split("T")[0])
                dt = datetime.fromisoformat(date_to_iso.split("T")[0])
                c_start = datetime(df.year, df.month, df.day, 0, 0, 0, tzinfo=tz_ist)
                c_end = datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=tz_ist)
                days_span = max(1, (c_end - c_start).days + 1)
                p_start = c_start - timedelta(days=days_span)
                p_end = c_start - timedelta(seconds=1)
                display_range = f"{c_start.strftime('%d %b %Y')} - {c_end.strftime('%d %b %Y')}"
                comp_label = "vs previous period"
            except Exception:
                c_start = datetime(now_ist.year, now_ist.month, 1, 0, 0, 0, tzinfo=tz_ist)
                c_end = today_end_ist
                p_start = datetime(now_ist.year, now_ist.month - 1 if now_ist.month > 1 else 12, 1, 0, 0, 0, tzinfo=tz_ist)
                p_end = c_start - timedelta(seconds=1)
                display_range = f"{c_start.strftime('%d %b')} - {c_end.strftime('%d %b %Y')}"
                comp_label = "vs last month"

        else:
            # this_month (Default)
            c_start = datetime(now_ist.year, now_ist.month, 1, 0, 0, 0, tzinfo=tz_ist)
            c_end = today_end_ist
            if now_ist.month == 1:
                p_start = datetime(now_ist.year - 1, 12, 1, 0, 0, 0, tzinfo=tz_ist)
            else:
                p_start = datetime(now_ist.year, now_ist.month - 1, 1, 0, 0, 0, tzinfo=tz_ist)
            p_end = c_start - timedelta(seconds=1)
            display_range = f"{c_start.strftime('%d %b')} - {c_end.strftime('%d %b %Y')}"
            comp_label = "vs last month"

        curr_start_utc = c_start.astimezone(timezone.utc)
        curr_end_utc = c_end.astimezone(timezone.utc)
        prev_start_utc = p_start.astimezone(timezone.utc)
        prev_end_utc = p_end.astimezone(timezone.utc)

        from_str = c_start.strftime("%Y-%m-%d")
        to_str = c_end.strftime("%Y-%m-%d")

        return (
            curr_start_utc,
            curr_end_utc,
            prev_start_utc,
            prev_end_utc,
            display_range,
            from_str,
            to_str,
            comp_label,
        )

    async def get_product_sales_performance(
        self,
        preset: str = "this_month",
        search: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> ProductSalesPerformanceResponse:
        """
        Fetch dynamic Sales, Orders, Stock KPIs, Sales Trend Curve, Inventory Summary,
        and Product-wise Sales table strictly without revenue metrics.
        """
        # Resolve date boundaries for current and comparison periods
        (
            curr_start,
            curr_end,
            prev_start,
            prev_end,
            display_range,
            from_str,
            to_str,
            comp_label,
        ) = self._resolve_date_range(preset, date_from, date_to)

        # -------------------------------------------------------------------
        # 1. ORDER & UNITS AGGREGATIONS (CURRENT PERIOD)
        # -------------------------------------------------------------------
        # Online Orders: All successfully placed orders in period (excluding cancelled)
        online_orders_curr_res = await self.db.execute(
            select(func.count(Order.id))
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.status) != "CANCELLED",
            )
        )
        online_orders_curr = online_orders_curr_res.scalar_one() or 0

        # Online Units Sold: Sum of item quantities in non-cancelled orders
        online_units_curr_res = await self.db.execute(
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.status) != "CANCELLED",
            )
        )
        online_units_curr = int(online_units_curr_res.scalar_one() or 0)

        # Offline Orders & Units Sold in period
        offline_curr_res = await self.db.execute(
            select(
                func.count(OfflineSale.id),
                func.coalesce(func.sum(OfflineSale.quantity), 0),
            ).where(
                OfflineSale.created_at >= curr_start,
                OfflineSale.created_at <= curr_end,
            )
        )
        offline_orders_curr, offline_units_curr = offline_curr_res.one()
        offline_orders_curr = int(offline_orders_curr or 0)
        offline_units_curr = int(offline_units_curr or 0)

        # Pending Orders: Placed orders awaiting processing/fulfillment
        pending_orders_curr_res = await self.db.execute(
            select(func.count(Order.id))
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.status).in_(["PENDING", "PROCESSING", "CONFIRMED", "PAYMENT_PENDING", "UNSHIPPED"]),
            )
        )
        pending_orders_curr = int(pending_orders_curr_res.scalar_one() or 0)

        # Cancelled Orders
        cancelled_orders_curr_res = await self.db.execute(
            select(func.count(Order.id))
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.status).in_(["CANCELLED", "REFUNDED"]),
            )
        )
        cancelled_orders_curr = int(cancelled_orders_curr_res.scalar_one() or 0)

        # Totals for current period
        total_orders_curr = online_orders_curr + offline_orders_curr
        total_units_curr = online_units_curr + offline_units_curr

        # -------------------------------------------------------------------
        # 2. ORDER & UNITS AGGREGATIONS (PREVIOUS PERIOD)
        # -------------------------------------------------------------------
        online_orders_prev_res = await self.db.execute(
            select(func.count(Order.id))
            .where(
                Order.created_at >= prev_start,
                Order.created_at <= prev_end,
                func.upper(Order.status) != "CANCELLED",
            )
        )
        online_orders_prev = online_orders_prev_res.scalar_one() or 0

        online_units_prev_res = await self.db.execute(
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.created_at >= prev_start,
                Order.created_at <= prev_end,
                func.upper(Order.status) != "CANCELLED",
            )
        )
        online_units_prev = int(online_units_prev_res.scalar_one() or 0)

        offline_prev_res = await self.db.execute(
            select(
                func.count(OfflineSale.id),
                func.coalesce(func.sum(OfflineSale.quantity), 0),
            ).where(
                OfflineSale.created_at >= prev_start,
                OfflineSale.created_at <= prev_end,
            )
        )
        offline_orders_prev, offline_units_prev = offline_prev_res.one()
        offline_orders_prev = int(offline_orders_prev or 0)
        offline_units_prev = int(offline_units_prev or 0)

        pending_orders_prev_res = await self.db.execute(
            select(func.count(Order.id))
            .where(
                Order.created_at >= prev_start,
                Order.created_at <= prev_end,
                func.upper(Order.status).in_(["PENDING", "PROCESSING", "CONFIRMED", "PAYMENT_PENDING", "UNSHIPPED"]),
            )
        )
        pending_orders_prev = int(pending_orders_prev_res.scalar_one() or 0)

        cancelled_orders_prev_res = await self.db.execute(
            select(func.count(Order.id))
            .where(
                Order.created_at >= prev_start,
                Order.created_at <= prev_end,
                func.upper(Order.status).in_(["CANCELLED", "REFUNDED"]),
            )
        )
        cancelled_orders_prev = int(cancelled_orders_prev_res.scalar_one() or 0)

        total_orders_prev = online_orders_prev + offline_orders_prev
        total_units_prev = online_units_prev + offline_units_prev

        # -------------------------------------------------------------------
        # 3. REAL-TIME CATALOG STOCK METRICS
        # -------------------------------------------------------------------
        stock_sum_res = await self.db.execute(
            select(func.coalesce(func.sum(Product.stock), 0)).where(Product.is_active.is_(True))
        )
        current_catalog_stock = int(stock_sum_res.scalar_one() or 0)

        low_stock_res = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.is_active.is_(True),
                Product.stock <= 10,
                Product.stock > 0,
            )
        )
        low_stock_count = int(low_stock_res.scalar_one() or 0)

        out_of_stock_res = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.is_active.is_(True),
                Product.stock <= 0,
            )
        )
        out_of_stock_count = int(out_of_stock_res.scalar_one() or 0)

        total_products_res = await self.db.execute(
            select(func.count(Product.id)).where(Product.is_active.is_(True))
        )
        total_catalog_products = int(total_products_res.scalar_one() or 0)

        # -------------------------------------------------------------------
        # 4. BUILD 10 SALES & STOCK KPI CARDS
        # -------------------------------------------------------------------
        kpis = SalesKPICard(
            total_orders=SalesMetricCard(
                current_value=float(total_orders_curr),
                previous_value=float(total_orders_prev),
                percentage_change=self._calc_pct_change(total_orders_curr, total_orders_prev),
                comparison_label=comp_label,
            ),
            total_units_sold=SalesMetricCard(
                current_value=float(total_units_curr),
                previous_value=float(total_units_prev),
                percentage_change=self._calc_pct_change(total_units_curr, total_units_prev),
                comparison_label=comp_label,
            ),
            online_orders=SalesMetricCard(
                current_value=float(online_orders_curr),
                previous_value=float(online_orders_prev),
                percentage_change=self._calc_pct_change(online_orders_curr, online_orders_prev),
                comparison_label=comp_label,
            ),
            online_units_sold=SalesMetricCard(
                current_value=float(online_units_curr),
                previous_value=float(online_units_prev),
                percentage_change=self._calc_pct_change(online_units_curr, online_units_prev),
                comparison_label=comp_label,
            ),
            offline_orders=SalesMetricCard(
                current_value=float(offline_orders_curr),
                previous_value=float(offline_orders_prev),
                percentage_change=self._calc_pct_change(offline_orders_curr, offline_orders_prev),
                comparison_label=comp_label,
            ),
            offline_units_sold=SalesMetricCard(
                current_value=float(offline_units_curr),
                previous_value=float(offline_units_prev),
                percentage_change=self._calc_pct_change(offline_units_curr, offline_units_prev),
                comparison_label=comp_label,
            ),
            pending_orders=SalesMetricCard(
                current_value=float(pending_orders_curr),
                previous_value=float(pending_orders_prev),
                percentage_change=self._calc_pct_change(pending_orders_curr, pending_orders_prev),
                comparison_label=comp_label,
            ),
            cancelled_orders=SalesMetricCard(
                current_value=float(cancelled_orders_curr),
                previous_value=float(cancelled_orders_prev),
                percentage_change=self._calc_pct_change(cancelled_orders_curr, cancelled_orders_prev),
                comparison_label=comp_label,
            ),
            current_stock=SalesMetricCard(
                current_value=float(current_catalog_stock),
                previous_value=float(current_catalog_stock),
                percentage_change=0.0,
                comparison_label="live catalog",
            ),
            low_stock_products=SalesMetricCard(
                current_value=float(low_stock_count + out_of_stock_count),
                previous_value=float(low_stock_count + out_of_stock_count),
                percentage_change=0.0,
                comparison_label=f"{out_of_stock_count} out of stock",
            ),
        )

        # -------------------------------------------------------------------
        # 5. SALES TREND TIME-SERIES CURVE
        # -------------------------------------------------------------------
        trend_days = max(1, min(60, (curr_end.date() - curr_start.date()).days + 1))
        trend_map: Dict[str, Dict[str, int]] = {}

        for d in range(trend_days):
            day_dt = curr_start.date() + timedelta(days=d)
            key = day_dt.strftime("%d %b")
            trend_map[key] = {
                "total_orders": 0,
                "online_orders": 0,
                "offline_orders": 0,
                "total_units": 0,
                "online_units": 0,
                "offline_units": 0,
            }

        # Daily Online Orders & Units
        daily_online_orders_res = await self.db.execute(
            select(
                func.date(Order.created_at).label("day"),
                func.count(Order.id).label("orders"),
            )
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.status) != "CANCELLED",
            )
            .group_by(func.date(Order.created_at))
        )
        for day_val, ord_count in daily_online_orders_res.all():
            k = day_val.strftime("%d %b") if hasattr(day_val, "strftime") else str(day_val)
            if k in trend_map:
                trend_map[k]["online_orders"] += int(ord_count)
                trend_map[k]["total_orders"] += int(ord_count)

        daily_online_units_res = await self.db.execute(
            select(
                func.date(Order.created_at).label("day"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.status) != "CANCELLED",
            )
            .group_by(func.date(Order.created_at))
        )
        for day_val, unit_count in daily_online_units_res.all():
            k = day_val.strftime("%d %b") if hasattr(day_val, "strftime") else str(day_val)
            if k in trend_map:
                trend_map[k]["online_units"] += int(unit_count)
                trend_map[k]["total_units"] += int(unit_count)

        # Daily Offline Sales & Units
        daily_offline_res = await self.db.execute(
            select(
                func.date(OfflineSale.created_at).label("day"),
                func.count(OfflineSale.id).label("sales_count"),
                func.coalesce(func.sum(OfflineSale.quantity), 0).label("units"),
            )
            .where(
                OfflineSale.created_at >= curr_start,
                OfflineSale.created_at <= curr_end,
            )
            .group_by(func.date(OfflineSale.created_at))
        )
        for day_val, off_count, off_units in daily_offline_res.all():
            k = day_val.strftime("%d %b") if hasattr(day_val, "strftime") else str(day_val)
            if k in trend_map:
                trend_map[k]["offline_orders"] += int(off_count)
                trend_map[k]["total_orders"] += int(off_count)
                trend_map[k]["offline_units"] += int(off_units)
                trend_map[k]["total_units"] += int(off_units)

        sales_trend: List[SalesTrendPoint] = [
            SalesTrendPoint(
                date=k,
                total_orders=v["total_orders"],
                online_orders=v["online_orders"],
                offline_orders=v["offline_orders"],
                total_units=v["total_units"],
                online_units=v["online_units"],
                offline_units=v["offline_units"],
            )
            for k, v in trend_map.items()
        ]

        # -------------------------------------------------------------------
        # 6. INVENTORY SUMMARY
        # -------------------------------------------------------------------
        inventory_summary = InventorySummary(
            current_stock=current_catalog_stock,
            sold_quantity=total_units_curr,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            total_catalog_products=total_catalog_products,
        )

        # -------------------------------------------------------------------
        # 7. PRODUCT-WISE SALES TABLE
        # -------------------------------------------------------------------
        prod_stmt = (
            select(Product)
            .outerjoin(Category, Product.category_id == Category.id)
            .where(Product.is_active.is_(True))
        )
        if search and search.strip():
            s = f"%{search.strip()}%"
            prod_stmt = prod_stmt.where(or_(Product.name.ilike(s), Category.name.ilike(s)))
        if category and category.upper() != "ALL":
            prod_stmt = prod_stmt.where(Category.name.ilike(f"%{category.strip()}%"))

        products_res = await self.db.execute(prod_stmt)
        products = products_res.scalars().all()

        # Online units per product in date range
        online_prod_units_stmt = (
            select(
                OrderItem.product_id,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
            )
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                func.upper(Order.status) != "CANCELLED",
            )
            .group_by(OrderItem.product_id)
        )
        online_prod_units_res = await self.db.execute(online_prod_units_stmt)
        online_prod_map = {p_id: int(u) for p_id, u in online_prod_units_res.all()}

        # Offline units per product name in date range
        offline_prod_units_stmt = (
            select(
                OfflineSale.product_name,
                func.coalesce(func.sum(OfflineSale.quantity), 0).label("units"),
            )
            .where(
                OfflineSale.created_at >= curr_start,
                OfflineSale.created_at <= curr_end,
            )
            .group_by(OfflineSale.product_name)
        )
        offline_prod_units_res = await self.db.execute(offline_prod_units_stmt)
        offline_prod_map = {name.lower(): int(u) for name, u in offline_prod_units_res.all()}

        product_items: List[ProductSalesPerformanceItem] = []
        for prod in products:
            on_u = online_prod_map.get(prod.id, 0)
            off_u = offline_prod_map.get(prod.name.lower(), 0)
            tot_u = on_u + off_u

            cat_str = str(prod.category).title() if prod.category else "Chocolates"

            product_items.append(
                ProductSalesPerformanceItem(
                    id=prod.id,
                    name=prod.name,
                    category_name=cat_str,
                    image_url=prod.image,
                    price=float(prod.price),
                    units_sold=tot_u,
                    online_units=on_u,
                    offline_units=off_u,
                    current_stock=int(prod.stock if prod.stock is not None else 0),
                )
            )

        # Sort products by total units sold descending
        product_items.sort(key=lambda p: (p.units_sold, p.current_stock), reverse=True)

        total_matching_products = len(product_items)
        offset = (page - 1) * limit
        paginated_products = product_items[offset : offset + limit]

        return ProductSalesPerformanceResponse(
            preset=preset,
            date_from=from_str,
            date_to=to_str,
            display_range=display_range,
            kpis=kpis,
            sales_trend=sales_trend,
            inventory_summary=inventory_summary,
            products=paginated_products,
            total_products=total_matching_products,
            page=page,
            limit=limit,
        )

    async def get_sales_analytics(
        self,
        preset: str = "this_month",
        search: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> ProductSalesPerformanceResponse:
        """Alias for get_product_sales_performance."""
        return await self.get_product_sales_performance(
            preset=preset,
            search=search,
            category=category,
            date_from=date_from,
            date_to=date_to,
            page=page,
            limit=limit,
        )

    async def get_online_sales_ledger(
        self,
        preset: Optional[str] = None,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        payment_method: Optional[str] = None,
        payment_status_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        date_from_iso: Optional[str] = None,
        date_to_iso: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> OnlineLedgerResponse:
        """Fetch paginated online sales ledger from orders table with preset support."""
        stmt = select(Order).options(selectinload(Order.user), selectinload(Order.items))

        # Handle period preset filtering
        if preset and preset.lower() != "all_time":
            (c_start, c_end, *_) = self._resolve_date_range(preset, date_from_iso, date_to_iso)
            stmt = stmt.where(Order.created_at >= c_start, Order.created_at <= c_end)
        elif date_from or date_to:
            if date_from:
                stmt = stmt.where(Order.created_at >= date_from)
            if date_to:
                stmt = stmt.where(Order.created_at <= date_to)

        if search and search.strip():
            s = f"%{search.strip()}%"
            stmt = stmt.join(User, Order.user_id == User.id, isouter=True).where(
                or_(
                    Order.id.ilike(s),
                    User.full_name.ilike(s),
                    User.email.ilike(s),
                )
            )

        if status_filter and status_filter.upper() != "ALL":
            stmt = stmt.where(func.upper(Order.status) == status_filter.strip().upper())

        if payment_method and payment_method.upper() != "ALL":
            stmt = stmt.where(Order.payment_method.ilike(f"%{payment_method.strip()}%"))

        if payment_status_filter and payment_status_filter.upper() != "ALL":
            psf = payment_status_filter.lower()
            if psf == "completed":
                stmt = stmt.where(func.upper(Order.payment_status) == "PAID")
            elif psf == "pending":
                stmt = stmt.where(func.upper(Order.payment_status).in_(["PENDING", "PROCESSING"]))
            elif psf in ["cancelled", "failed"]:
                stmt = stmt.where(func.upper(Order.payment_status).in_(["FAILED", "CANCELLED", "REFUNDED", "REFUND PENDING", "PARTIALLY REFUNDED"]))
            else:
                stmt = stmt.where(func.upper(Order.payment_status) == psf.upper())

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
            cust_name = ord_obj.user.full_name if ord_obj.user else "Customer"
            cust_email = ord_obj.user.email if ord_obj.user else "N/A"

            # Create product summary string
            prod_names = []
            tot_qty = 0
            if ord_obj.items:
                for itm in ord_obj.items:
                    tot_qty += itm.quantity
                    p_name = itm.product.name if itm.product else "Chocolate Item"
                    prod_names.append(f"{p_name} (x{itm.quantity})")

            prod_summary = ", ".join(prod_names) if prod_names else "Assorted Chocolates"

            # Clean & proper Order ID resolution: never chop or double-prefix
            ord_raw = str(ord_obj.id or "")
            if ord_raw.upper().startswith("ORD-"):
                display_ord_id = ord_raw
            elif len(ord_raw) > 12:
                display_ord_id = f"ORD-{ord_raw[:8].upper()}"
            else:
                display_ord_id = ord_raw

            items.append(
                OnlineLedgerItem(
                    id=ord_obj.id,
                    order_id=display_ord_id,
                    created_at=ord_obj.created_at.strftime("%d %b %Y, %I:%M %p") if ord_obj.created_at else "Recent",
                    customer_name=cust_name,
                    customer_email=cust_email,
                    product_summary=prod_summary,
                    quantity=tot_qty if tot_qty > 0 else 1,
                    payment_method=ord_obj.payment_method or "UPI",
                    amount=round(float(ord_obj.total or 0.0), 2),
                    order_status=ord_obj.status or "Processing",
                    payment_status=ord_obj.payment_status or "PAID",
                    subtotal=round(float(ord_obj.subtotal or ord_obj.total or 0.0), 2),
                    discount=round(float(ord_obj.discount or ord_obj.coupon_discount or 0.0), 2),
                    delivery_option=ord_obj.delivery_option or "Standard Delivery",
                    shipping_address=ord_obj.shipping_address if isinstance(ord_obj.shipping_address, dict) else None,
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
        preset: Optional[str] = None,
        search: Optional[str] = None,
        payment_method: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        date_from_iso: Optional[str] = None,
        date_to_iso: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> OfflineLedgerResponse:
        """Fetch paginated offline sales ledger from offline_sales table with preset support."""
        stmt = select(OfflineSale)

        # Handle period preset filtering
        if preset and preset.lower() != "all_time":
            (c_start, c_end, *_) = self._resolve_date_range(preset, date_from_iso, date_to_iso)
            stmt = stmt.where(OfflineSale.created_at >= c_start, OfflineSale.created_at <= c_end)
        elif date_from or date_to:
            if date_from:
                stmt = stmt.where(OfflineSale.created_at >= date_from)
            if date_to:
                stmt = stmt.where(OfflineSale.created_at <= date_to)

        if search and search.strip():
            s = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    OfflineSale.id.ilike(s),
                    OfflineSale.product_name.ilike(s),
                    OfflineSale.receipt_id.ilike(s),
                    OfflineSale.company_name.ilike(s),
                    OfflineSale.contact_person.ilike(s),
                )
            )

        if payment_method and payment_method.upper() != "ALL":
            stmt = stmt.where(OfflineSale.payment_method.ilike(f"%{payment_method.strip()}%"))

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
            rec_id = getattr(sale, 'receipt_id', None) or getattr(sale, 'receipt_number', None)
            if rec_id:
                clean_rec = str(rec_id).strip()
                display_receipt_id = clean_rec if clean_rec.upper().startswith("POS-") or clean_rec.upper().startswith("OFF-") else f"POS-{clean_rec}"
            else:
                display_receipt_id = f"POS-{sale.id[:8].upper()}"

            cust_name = getattr(sale, 'company_name', None) or getattr(sale, 'contact_person', None) or "Walk-in Customer"
            phone = getattr(sale, 'phone', None) or "N/A"

            items.append(
                OfflineLedgerItem(
                    id=sale.id,
                    receipt_id=display_receipt_id,
                    created_at=sale.created_at.strftime("%d %b %Y, %I:%M %p") if sale.created_at else "Recent",
                    product_name=sale.product_name or "Handcrafted Chocolate Box",
                    quantity=sale.quantity if sale.quantity else 1,
                    payment_method=sale.payment_method or "Cash",
                    amount=round(float(sale.total_price or sale.total_amount or 0.0), 2),
                    customer_name=cust_name,
                    phone=phone,
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
        preset: str = "this_month",
        search: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        """Generates CSV report based on active tab view."""
        output = io.StringIO()
        writer = csv.writer(output)

        if tab == "online":
            (c_start, c_end, *_) = self._resolve_date_range(preset, date_from, date_to)
            ledger = await self.get_online_sales_ledger(preset=preset, search=search, date_from_iso=date_from, date_to_iso=date_to, page=1, limit=5000)
            writer.writerow(["CHOVIQUE ONLINE ORDERS REPORT"])
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
            (c_start, c_end, *_) = self._resolve_date_range(preset, date_from, date_to)
            ledger = await self.get_offline_sales_ledger(preset=preset, search=search, date_from_iso=date_from, date_to_iso=date_to, page=1, limit=5000)
            writer.writerow(["CHOVIQUE IN-STORE SALES REPORT"])
            writer.writerow(["Receipt ID", "Date", "Customer / Company", "Phone", "Product Name", "Quantity", "Payment Method", "Amount (INR)"])
            for item in ledger.items:
                writer.writerow([
                    item.receipt_id,
                    item.created_at,
                    item.customer_name or "Walk-in Customer",
                    item.phone or "N/A",
                    item.product_name,
                    item.quantity,
                    item.payment_method,
                    item.amount,
                ])

        else:
            # Products Sales & Stock (Default)
            perf = await self.get_product_sales_performance(
                preset=preset,
                search=search,
                category=category,
                date_from=date_from,
                date_to=date_to,
                page=1,
                limit=5000,
            )
            writer.writerow(["CHOVIQUE PRODUCT SALES & STOCK REPORT"])
            writer.writerow([f"Period: {perf.display_range}"])
            writer.writerow([])
            writer.writerow(["SUMMARY KPIS"])
            writer.writerow(["Total Orders", int(perf.kpis.total_orders.current_value)])
            writer.writerow(["Total Units Sold", int(perf.kpis.total_units_sold.current_value)])
            writer.writerow(["Online Orders", int(perf.kpis.online_orders.current_value)])
            writer.writerow(["Online Units Sold", int(perf.kpis.online_units_sold.current_value)])
            writer.writerow(["Offline Orders", int(perf.kpis.offline_orders.current_value)])
            writer.writerow(["Offline Units Sold", int(perf.kpis.offline_units_sold.current_value)])
            writer.writerow(["Pending Orders", int(perf.kpis.pending_orders.current_value)])
            writer.writerow(["Cancelled Orders", int(perf.kpis.cancelled_orders.current_value)])
            writer.writerow(["Current Available Stock", int(perf.kpis.current_stock.current_value)])
            writer.writerow(["Low Stock / Out of Stock Products", int(perf.kpis.low_stock_products.current_value)])
            writer.writerow([])
            writer.writerow(["PRODUCT-WISE SALES & STOCK PERFORMANCE"])
            writer.writerow(["Product Name", "Category", "Price (INR)", "Units Sold", "Online Units", "Offline Units", "Current Stock"])
            for item in perf.products:
                writer.writerow([
                    item.name,
                    item.category_name,
                    item.price,
                    item.units_sold,
                    item.online_units,
                    item.offline_units,
                    item.current_stock,
                ])

        return output.getvalue()
