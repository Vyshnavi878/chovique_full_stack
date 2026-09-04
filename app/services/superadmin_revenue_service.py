import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.user import User
from app.schemas.superadmin_revenue import (
    KPICardWithComparison,
    PaymentMethodRevenue,
    RevenueSummaryRow,
    RevenueTrendDataPoint,
    SuperadminRevenueResponse,
    TransactionOrderRow,
)


class SuperadminRevenueService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_time_bounds(
        self,
        preset: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[datetime, datetime, datetime, datetime, str]:
        """Calculates current period and previous period bounds based on preset filter in UTC/IST."""
        now = datetime.now(timezone.utc)
        preset_lower = (preset or "this_month").lower().strip()

        if preset_lower in ("today",):
            curr_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            prev_start = curr_start - timedelta(days=1)
            prev_end = curr_start - timedelta(seconds=1)
            comparison_label = "vs yesterday"

        elif preset_lower in ("yesterday",):
            yesterday = now - timedelta(days=1)
            curr_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=timezone.utc)
            curr_end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, tzinfo=timezone.utc)
            day_before = yesterday - timedelta(days=1)
            prev_start = datetime(day_before.year, day_before.month, day_before.day, 0, 0, 0, tzinfo=timezone.utc)
            prev_end = curr_start - timedelta(seconds=1)
            comparison_label = "vs day before"

        elif preset_lower in ("last_7_days", "7days", "week"):
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            curr_start = (curr_end - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            prev_end = curr_start - timedelta(seconds=1)
            prev_start = (prev_end - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            comparison_label = "vs previous 7 days"

        elif preset_lower in ("last_30_days", "30days"):
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            curr_start = (curr_end - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
            prev_end = curr_start - timedelta(seconds=1)
            prev_start = (prev_end - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
            comparison_label = "vs previous 30 days"

        elif preset_lower in ("last_month",):
            # First day of previous month to last day of previous month
            if now.month == 1:
                curr_start = datetime(now.year - 1, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
                curr_end = datetime(now.year - 1, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                prev_start = datetime(now.year - 1, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
                prev_end = datetime(now.year - 1, 11, 30, 23, 59, 59, tzinfo=timezone.utc)
            else:
                curr_start = datetime(now.year, now.month - 1, 1, 0, 0, 0, tzinfo=timezone.utc)
                # Last day of prev month
                first_of_this_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
                curr_end = first_of_this_month - timedelta(seconds=1)
                if now.month == 2:
                    prev_start = datetime(now.year - 1, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
                    prev_end = datetime(now.year - 1, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                else:
                    prev_start = datetime(now.year, now.month - 2, 1, 0, 0, 0, tzinfo=timezone.utc)
                    prev_end = curr_start - timedelta(seconds=1)
            comparison_label = "vs prior month"

        elif preset_lower in ("custom",) and date_from and date_to:
            curr_start = date_from if date_from.tzinfo else date_from.replace(tzinfo=timezone.utc)
            curr_end = date_to if date_to.tzinfo else date_to.replace(tzinfo=timezone.utc)
            if curr_start.hour == 0 and curr_start.minute == 0 and curr_end.hour == 0 and curr_end.minute == 0:
                curr_end = curr_end.replace(hour=23, minute=59, second=59)
            delta = curr_end - curr_start
            prev_end = curr_start - timedelta(seconds=1)
            prev_start = curr_start - delta
            comparison_label = "vs previous period"

        else:
            # Default: This Month ("this_month" / "month")
            curr_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            if now.month == 1:
                prev_start = datetime(now.year - 1, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
                prev_end = curr_start - timedelta(seconds=1)
            else:
                prev_start = datetime(now.year, now.month - 1, 1, 0, 0, 0, tzinfo=timezone.utc)
                prev_end = curr_start - timedelta(seconds=1)
            comparison_label = "vs last month"

        return curr_start, curr_end, prev_start, prev_end, comparison_label

    def _calc_pct_change(self, current: float, previous: float) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    async def get_revenue_analytics(
        self,
        preset: str = "this_month",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        date_basis: str = "order_date",
    ) -> SuperadminRevenueResponse:
        """Fetch complete revenue and sales analytics with 8 KPI cards, multi-metric trend, and transaction breakdown."""
        curr_start, curr_end, prev_start, prev_end, comp_label = self._get_time_bounds(
            preset, date_from, date_to
        )

        basis = (date_basis or "order_date").lower().strip()
        if basis not in ("order_date", "payment_date"):
            basis = "order_date"

        cod_methods = ["COD", "CASH ON DELIVERY"]

        # Helper expressions for filtering
        def build_period_metrics_query(start_dt: datetime, end_dt: datetime):
            if basis == "payment_date":
                # For revenue metrics: filter by effective payment date (paid_at or created_at)
                paid_date_col = func.coalesce(Order.paid_at, Order.created_at)
                
                # Paid Online Revenue
                q_online_rev = select(func.coalesce(func.sum(Order.total), 0.0)).where(
                    paid_date_col >= start_dt,
                    paid_date_col <= end_dt,
                    func.upper(Order.payment_status) == "PAID",
                    ~func.upper(Order.payment_method).in_(cod_methods),
                )
                
                # Paid COD Collected
                q_cod_collected = select(func.coalesce(func.sum(Order.total), 0.0)).where(
                    paid_date_col >= start_dt,
                    paid_date_col <= end_dt,
                    func.upper(Order.payment_status) == "PAID",
                    func.upper(Order.payment_method).in_(cod_methods),
                )
                
                # Pending Payment Amount
                q_pending_payment = select(func.coalesce(func.sum(Order.total), 0.0)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_status) == "PENDING",
                )
                
                # Order counts (Placed in this period)
                q_total_orders = select(func.count(Order.id)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                )
                
                # Paid orders (where payment received in this period)
                q_paid_orders = select(func.count(Order.id)).where(
                    paid_date_col >= start_dt,
                    paid_date_col <= end_dt,
                    func.upper(Order.payment_status) == "PAID",
                )
                
                # COD orders placed in period
                q_cod_orders = select(func.count(Order.id)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_method).in_(cod_methods),
                )
                
                # Pending orders placed in period
                q_pending_orders = select(func.count(Order.id)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_status) == "PENDING",
                )
            else:
                # Order Date Basis: Everything evaluated against Order.created_at
                q_online_rev = select(func.coalesce(func.sum(Order.total), 0.0)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_status) == "PAID",
                    ~func.upper(Order.payment_method).in_(cod_methods),
                )
                
                q_cod_collected = select(func.coalesce(func.sum(Order.total), 0.0)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_status) == "PAID",
                    func.upper(Order.payment_method).in_(cod_methods),
                )
                
                q_pending_payment = select(func.coalesce(func.sum(Order.total), 0.0)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_status) == "PENDING",
                )
                
                q_total_orders = select(func.count(Order.id)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                )
                
                q_paid_orders = select(func.count(Order.id)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_status) == "PAID",
                )
                
                q_cod_orders = select(func.count(Order.id)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_method).in_(cod_methods),
                )
                
                q_pending_orders = select(func.count(Order.id)).where(
                    Order.created_at >= start_dt,
                    Order.created_at <= end_dt,
                    func.upper(Order.payment_status) == "PENDING",
                )

            return (
                q_online_rev,
                q_cod_collected,
                q_pending_payment,
                q_total_orders,
                q_paid_orders,
                q_cod_orders,
                q_pending_orders,
            )

        # -------------------------------------------------------------
        # 1. Fetch Current Period Metrics
        # -------------------------------------------------------------
        (
            q_on_rev,
            q_cod_col,
            q_pend_pay,
            q_tot_ord,
            q_pd_ord,
            q_cod_ord,
            q_pend_ord,
        ) = build_period_metrics_query(curr_start, curr_end)

        curr_online_rev = (await self.db.execute(q_on_rev)).scalar_one() or 0.0
        curr_cod_col = (await self.db.execute(q_cod_col)).scalar_one() or 0.0
        curr_pending_pay = (await self.db.execute(q_pend_pay)).scalar_one() or 0.0
        curr_total_orders = (await self.db.execute(q_tot_ord)).scalar_one() or 0
        curr_paid_orders = (await self.db.execute(q_pd_ord)).scalar_one() or 0
        curr_cod_orders = (await self.db.execute(q_cod_ord)).scalar_one() or 0
        curr_pending_orders = (await self.db.execute(q_pend_ord)).scalar_one() or 0

        curr_total_revenue = curr_online_rev + curr_cod_col

        # -------------------------------------------------------------
        # 2. Fetch Previous Period Metrics
        # -------------------------------------------------------------
        (
            pq_on_rev,
            pq_cod_col,
            pq_pend_pay,
            pq_tot_ord,
            pq_pd_ord,
            pq_cod_ord,
            pq_pend_ord,
        ) = build_period_metrics_query(prev_start, prev_end)

        prev_online_rev = (await self.db.execute(pq_on_rev)).scalar_one() or 0.0
        prev_cod_col = (await self.db.execute(pq_cod_col)).scalar_one() or 0.0
        prev_pending_pay = (await self.db.execute(pq_pend_pay)).scalar_one() or 0.0
        prev_total_orders = (await self.db.execute(pq_tot_ord)).scalar_one() or 0
        prev_paid_orders = (await self.db.execute(pq_pd_ord)).scalar_one() or 0
        prev_cod_orders = (await self.db.execute(pq_cod_ord)).scalar_one() or 0
        prev_pending_orders = (await self.db.execute(pq_pend_ord)).scalar_one() or 0

        prev_total_revenue = prev_online_rev + prev_cod_col

        # -------------------------------------------------------------
        # 3. Construct 8 KPI Cards
        # -------------------------------------------------------------
        kpi_total_revenue = KPICardWithComparison(
            current_value=round(curr_total_revenue, 2),
            previous_value=round(prev_total_revenue, 2),
            percentage_change=self._calc_pct_change(curr_total_revenue, prev_total_revenue),
            comparison_label=comp_label,
        )

        kpi_online_revenue = KPICardWithComparison(
            current_value=round(curr_online_rev, 2),
            previous_value=round(prev_online_rev, 2),
            percentage_change=self._calc_pct_change(curr_online_rev, prev_online_rev),
            comparison_label=comp_label,
        )

        kpi_cod_collected = KPICardWithComparison(
            current_value=round(curr_cod_col, 2),
            previous_value=round(prev_cod_col, 2),
            percentage_change=self._calc_pct_change(curr_cod_col, prev_cod_col),
            comparison_label=comp_label,
        )

        kpi_pending_payment = KPICardWithComparison(
            current_value=round(curr_pending_pay, 2),
            previous_value=round(prev_pending_pay, 2),
            percentage_change=self._calc_pct_change(curr_pending_pay, prev_pending_pay),
            comparison_label=comp_label,
        )

        kpi_total_orders = KPICardWithComparison(
            current_value=float(curr_total_orders),
            previous_value=float(prev_total_orders),
            percentage_change=self._calc_pct_change(curr_total_orders, prev_total_orders),
            comparison_label=comp_label,
        )

        kpi_paid_orders = KPICardWithComparison(
            current_value=float(curr_paid_orders),
            previous_value=float(prev_paid_orders),
            percentage_change=self._calc_pct_change(curr_paid_orders, prev_paid_orders),
            comparison_label=comp_label,
        )

        kpi_cod_orders = KPICardWithComparison(
            current_value=float(curr_cod_orders),
            previous_value=float(prev_cod_orders),
            percentage_change=self._calc_pct_change(curr_cod_orders, prev_cod_orders),
            comparison_label=comp_label,
        )

        kpi_pending_orders = KPICardWithComparison(
            current_value=float(curr_pending_orders),
            previous_value=float(prev_pending_orders),
            percentage_change=self._calc_pct_change(curr_pending_orders, prev_pending_orders),
            comparison_label=comp_label,
        )

        # -------------------------------------------------------------
        # 4. Fetch Detailed Orders for Transactions & Daily Time Series
        # -------------------------------------------------------------
        order_filter = (
            or_(
                and_(Order.created_at >= curr_start, Order.created_at <= curr_end),
                and_(
                    func.coalesce(Order.paid_at, Order.created_at) >= curr_start,
                    func.coalesce(Order.paid_at, Order.created_at) <= curr_end,
                ),
            )
            if basis == "payment_date"
            else and_(Order.created_at >= curr_start, Order.created_at <= curr_end)
        )

        orders_res = await self.db.execute(
            select(Order)
            .options(selectinload(Order.user))
            .where(order_filter)
            .order_by(Order.created_at.desc())
        )
        orders_list = list(orders_res.scalars().all())

        # Construct Transactions List
        transactions: List[TransactionOrderRow] = []
        payment_method_totals: Dict[str, Dict[str, float]] = {}

        for o in orders_list:
            u_name = o.user.full_name if o.user and o.user.full_name else (o.shipping_address.get("name") if isinstance(o.shipping_address, dict) else "Customer")
            u_email = o.user.email if o.user and o.user.email else ""
            u_phone = o.user.phone if o.user and o.user.phone else (o.shipping_address.get("phone") if isinstance(o.shipping_address, dict) else "")

            p_date_str = o.paid_at.strftime("%d %b %Y, %I:%M %p") if o.paid_at else (
                o.created_at.strftime("%d %b %Y, %I:%M %p") if o.payment_status.upper() == "PAID" else None
            )

            transactions.append(
                TransactionOrderRow(
                    order_id=o.id,
                    customer_name=u_name or "Guest Customer",
                    customer_email=u_email or "",
                    customer_phone=u_phone or "",
                    order_date=o.created_at.strftime("%d %b %Y, %I:%M %p"),
                    payment_date=p_date_str,
                    amount=round(float(o.total or 0.0), 2),
                    payment_method=o.payment_method or "UPI",
                    payment_status=(o.payment_status or "PENDING").upper(),
                    order_status=o.status or "Processing",
                )
            )

            # Payment method aggregation (only for collected revenue)
            if o.payment_status.upper() == "PAID":
                pm_key = o.payment_method.strip() if o.payment_method else "UPI"
                if pm_key not in payment_method_totals:
                    payment_method_totals[pm_key] = {"amount": 0.0, "count": 0}
                payment_method_totals[pm_key]["amount"] += float(o.total or 0.0)
                payment_method_totals[pm_key]["count"] += 1

        # Payment Method Breakdown List
        pm_list: List[PaymentMethodRevenue] = []
        for pm_name, pm_data in payment_method_totals.items():
            pm_pct = round((pm_data["amount"] / curr_total_revenue * 100), 1) if curr_total_revenue > 0 else 0.0
            pm_list.append(
                PaymentMethodRevenue(
                    method=pm_name,
                    amount=round(pm_data["amount"], 2),
                    percentage=pm_pct,
                    orders_count=pm_data["count"],
                )
            )
        pm_list.sort(key=lambda x: x.amount, reverse=True)

        # -------------------------------------------------------------
        # 5. Day-by-Day Time Series & Summary Rows
        # -------------------------------------------------------------
        days_map: Dict[str, Dict[str, float]] = {}
        curr = curr_start
        while curr <= curr_end:
            d_str = curr.strftime("%Y-%m-%d")
            days_map[d_str] = {
                "total_orders": 0,
                "paid_orders": 0,
                "cod_orders": 0,
                "pending_orders": 0,
                "total_revenue": 0.0,
                "online_revenue": 0.0,
                "cod_collected": 0.0,
                "pending_payment": 0.0,
            }
            curr += timedelta(days=1)

        for o in orders_list:
            is_cod = (o.payment_method or "").upper() in cod_methods
            is_paid = (o.payment_status or "").upper() == "PAID"
            is_pending = (o.payment_status or "").upper() == "PENDING"
            amt = float(o.total or 0.0)

            # Date key based on selected dimension
            if basis == "payment_date" and is_paid:
                effective_date = o.paid_at or o.created_at
                d_key = effective_date.strftime("%Y-%m-%d")
            else:
                d_key = o.created_at.strftime("%Y-%m-%d")

            if d_key in days_map:
                if is_paid:
                    days_map[d_key]["total_revenue"] += amt
                    days_map[d_key]["paid_orders"] += 1
                    if is_cod:
                        days_map[d_key]["cod_collected"] += amt
                    else:
                        days_map[d_key]["online_revenue"] += amt
                elif is_pending:
                    days_map[d_key]["pending_payment"] += amt
                    days_map[d_key]["pending_orders"] += 1

                # Order placed counts
                o_create_key = o.created_at.strftime("%Y-%m-%d")
                if o_create_key in days_map:
                    days_map[o_create_key]["total_orders"] += 1
                    if is_cod:
                        days_map[o_create_key]["cod_orders"] += 1

        revenue_trend: List[RevenueTrendDataPoint] = []
        summary_rows: List[RevenueSummaryRow] = []

        sorted_dates = sorted(days_map.keys())
        delta_days = max(1, len(sorted_dates))
        step_days = max(1, delta_days // 15) if delta_days > 15 else 1

        for idx, d_str in enumerate(sorted_dates):
            d_info = days_map[d_str]
            tot_rev = round(d_info["total_revenue"], 2)
            on_rev = round(d_info["online_revenue"], 2)
            cod_col = round(d_info["cod_collected"], 2)
            pend_pay = round(d_info["pending_payment"], 2)
            tot_ord = int(d_info["total_orders"])
            pd_ord = int(d_info["paid_orders"])
            cod_ord = int(d_info["cod_orders"])
            pend_ord = int(d_info["pending_orders"])
            aov = round(tot_rev / pd_ord, 2) if pd_ord > 0 else 0.0

            dt_obj = datetime.strptime(d_str, "%Y-%m-%d")
            date_label = dt_obj.strftime("%d %b")

            if idx % step_days == 0 or idx == len(sorted_dates) - 1:
                revenue_trend.append(
                    RevenueTrendDataPoint(
                        date=date_label,
                        total_revenue=tot_rev,
                        online_revenue=on_rev,
                        cod_collected=cod_col,
                        pending_payment=pend_pay,
                        total_orders=tot_ord,
                        paid_orders=pd_ord,
                        cod_orders=cod_ord,
                        pending_orders=pend_ord,
                    )
                )

            summary_rows.append(
                RevenueSummaryRow(
                    date=d_str,
                    total_orders=tot_ord,
                    paid_orders=pd_ord,
                    cod_orders=cod_ord,
                    pending_orders=pend_ord,
                    total_revenue=tot_rev,
                    online_revenue=on_rev,
                    cod_collected=cod_col,
                    pending_payment=pend_pay,
                    avg_order_value=aov,
                )
            )

        summary_rows.sort(key=lambda r: r.date, reverse=True)
        display_range = f"{curr_start.strftime('%d %b %Y')} - {curr_end.strftime('%d %b %Y')}"

        return SuperadminRevenueResponse(
            preset=preset,
            date_basis=basis,
            date_from=curr_start.isoformat(),
            date_to=curr_end.isoformat(),
            display_range=display_range,
            total_revenue=kpi_total_revenue,
            online_revenue=kpi_online_revenue,
            cod_collected=kpi_cod_collected,
            pending_payment=kpi_pending_payment,
            total_orders=kpi_total_orders,
            paid_orders=kpi_paid_orders,
            cod_orders=kpi_cod_orders,
            pending_orders=kpi_pending_orders,
            revenue_trend=revenue_trend,
            revenue_by_payment_method=pm_list,
            transactions=transactions,
            summary_rows=summary_rows,
        )

    async def generate_revenue_csv(
        self,
        preset: str = "this_month",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        date_basis: str = "order_date",
    ) -> str:
        """Generates downloadable CSV text for revenue performance analytics and transaction breakdown."""
        analytics = await self.get_revenue_analytics(preset, date_from, date_to, date_basis)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["=== CHOVIQUE SUPER ADMIN REVENUE & SALES ANALYTICS REPORT ==="])
        writer.writerow(["Date Range", analytics.display_range])
        writer.writerow(["Filter Preset", analytics.preset])
        writer.writerow(["Date Filter Basis", "Order Date (Placed)" if analytics.date_basis == "order_date" else "Payment Date (Collected)"])
        writer.writerow([])

        # KPI Summary Table
        writer.writerow(["--- KEY PERFORMANCE INDICATORS ---"])
        writer.writerow(["Metric", "Current Period", "Previous Period", "Growth %", "Comparison"])
        writer.writerow(["Total Revenue (₹)", analytics.total_revenue.current_value, analytics.total_revenue.previous_value, analytics.total_revenue.percentage_change, analytics.total_revenue.comparison_label])
        writer.writerow(["Online Revenue (₹)", analytics.online_revenue.current_value, analytics.online_revenue.previous_value, analytics.online_revenue.percentage_change, analytics.online_revenue.comparison_label])
        writer.writerow(["COD Collected (₹)", analytics.cod_collected.current_value, analytics.cod_collected.previous_value, analytics.cod_collected.percentage_change, analytics.cod_collected.comparison_label])
        writer.writerow(["Pending Payment (₹)", analytics.pending_payment.current_value, analytics.pending_payment.previous_value, analytics.pending_payment.percentage_change, analytics.pending_payment.comparison_label])
        writer.writerow(["Total Orders", int(analytics.total_orders.current_value), int(analytics.total_orders.previous_value), analytics.total_orders.percentage_change, analytics.total_orders.comparison_label])
        writer.writerow(["Paid Orders", int(analytics.paid_orders.current_value), int(analytics.paid_orders.previous_value), analytics.paid_orders.percentage_change, analytics.paid_orders.comparison_label])
        writer.writerow(["COD Orders", int(analytics.cod_orders.current_value), int(analytics.cod_orders.previous_value), analytics.cod_orders.percentage_change, analytics.cod_orders.comparison_label])
        writer.writerow(["Pending Orders", int(analytics.pending_orders.current_value), int(analytics.pending_orders.previous_value), analytics.pending_orders.percentage_change, analytics.pending_orders.comparison_label])
        writer.writerow([])

        # Payment Methods
        writer.writerow(["--- REVENUE BY PAYMENT METHOD ---"])
        writer.writerow(["Payment Method", "Amount Collected (₹)", "Share %", "Paid Orders Count"])
        for pm in analytics.revenue_by_payment_method:
            writer.writerow([pm.method, pm.amount, f"{pm.percentage}%", pm.orders_count])
        writer.writerow([])

        # Transactions
        writer.writerow(["--- DETAILED ORDER TRANSACTIONS ---"])
        writer.writerow(["Order ID", "Customer Name", "Customer Email", "Customer Phone", "Order Date", "Payment Date", "Amount (₹)", "Payment Method", "Payment Status", "Order Status"])
        for tx in analytics.transactions:
            writer.writerow([
                tx.order_id,
                tx.customer_name,
                tx.customer_email,
                tx.customer_phone,
                tx.order_date,
                tx.payment_date or "N/A",
                tx.amount,
                tx.payment_method,
                tx.payment_status,
                tx.order_status,
            ])
        writer.writerow([])

        # Daily Summary
        writer.writerow(["--- DAILY PERFORMANCE SUMMARY ---"])
        writer.writerow(["Date", "Total Orders", "Paid Orders", "COD Orders", "Pending Orders", "Total Revenue (₹)", "Online Revenue (₹)", "COD Collected (₹)", "Pending Payment (₹)", "Avg Order Value (₹)"])
        for row in analytics.summary_rows:
            writer.writerow([
                row.date,
                row.total_orders,
                row.paid_orders,
                row.cod_orders,
                row.pending_orders,
                row.total_revenue,
                row.online_revenue,
                row.cod_collected,
                row.pending_payment,
                row.avg_order_value,
            ])

        return output.getvalue()
