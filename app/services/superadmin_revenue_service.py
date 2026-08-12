import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offline_sale import OfflineSale
from app.models.order import Order
from app.schemas.superadmin_revenue import (
    KPICardWithComparison,
    PaymentMethodRevenue,
    RevenueBySource,
    RevenueSummaryRow,
    RevenueTrendDataPoint,
    SuperadminRevenueResponse,
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
        """Calculates current period and previous period bounds based on preset filter."""
        now = datetime.now(timezone.utc)
        preset_lower = (preset or "month").lower()

        if preset_lower == "today":
            curr_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            prev_start = curr_start - timedelta(days=1)
            prev_end = curr_start - timedelta(seconds=1)
            comparison_label = "vs yesterday"

        elif preset_lower == "week":
            # Monday of current week
            curr_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            prev_start = curr_start - timedelta(days=7)
            prev_end = curr_start - timedelta(seconds=1)
            comparison_label = "vs last week"

        elif preset_lower == "3months":
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            curr_start = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
            prev_end = curr_start - timedelta(seconds=1)
            prev_start = curr_start - timedelta(days=90)
            comparison_label = "vs previous 3 months"

        elif preset_lower == "year":
            curr_start = datetime(now.year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            prev_start = datetime(now.year - 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            prev_end = datetime(now.year - 1, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            comparison_label = "vs last year"

        elif preset_lower == "custom" and date_from and date_to:
            curr_start = date_from if date_from.tzinfo else date_from.replace(tzinfo=timezone.utc)
            curr_end = date_to if date_to.tzinfo else date_to.replace(tzinfo=timezone.utc)
            delta = curr_end - curr_start
            prev_end = curr_start - timedelta(seconds=1)
            prev_start = curr_start - delta
            comparison_label = "vs previous period"

        else:
            # Default: Month ("month")
            curr_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            curr_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            
            # Previous month
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
        preset: str = "month",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> SuperadminRevenueResponse:
        """Fetch complete revenue analytics data."""
        curr_start, curr_end, prev_start, prev_end, comp_label = self._get_time_bounds(
            preset, date_from, date_to
        )

        valid_order_statuses = ["Paid", "Delivered", "Shipped", "Processing"]

        # -------------------------------------------------------------
        # 1. Current Period Metrics
        # -------------------------------------------------------------
        # Current Online Revenue & Orders
        online_curr_res = await self.db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0.0),
                func.count(Order.id),
            ).where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                Order.status.in_(valid_order_statuses),
            )
        )
        online_curr_rev, online_curr_orders = online_curr_res.one()

        # Current Offline Revenue & Sales
        offline_curr_res = await self.db.execute(
            select(
                func.coalesce(func.sum(OfflineSale.total_price), 0.0),
                func.count(OfflineSale.id),
            ).where(
                OfflineSale.created_at >= curr_start,
                OfflineSale.created_at <= curr_end,
            )
        )
        offline_curr_rev, offline_curr_sales = offline_curr_res.one()

        total_curr_rev = online_curr_rev + offline_curr_rev
        total_curr_count = online_curr_orders + offline_curr_sales
        curr_aov = round(total_curr_rev / total_curr_count, 2) if total_curr_count > 0 else 0.0

        # -------------------------------------------------------------
        # 2. Previous Period Metrics (for comparison)
        # -------------------------------------------------------------
        online_prev_res = await self.db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0.0),
                func.count(Order.id),
            ).where(
                Order.created_at >= prev_start,
                Order.created_at <= prev_end,
                Order.status.in_(valid_order_statuses),
            )
        )
        online_prev_rev, online_prev_orders = online_prev_res.one()

        offline_prev_res = await self.db.execute(
            select(
                func.coalesce(func.sum(OfflineSale.total_price), 0.0),
                func.count(OfflineSale.id),
            ).where(
                OfflineSale.created_at >= prev_start,
                OfflineSale.created_at <= prev_end,
            )
        )
        offline_prev_rev, offline_prev_sales = offline_prev_res.one()

        total_prev_rev = online_prev_rev + offline_prev_rev
        total_prev_count = online_prev_orders + offline_prev_sales
        prev_aov = round(total_prev_rev / total_prev_count, 2) if total_prev_count > 0 else 0.0

        # -------------------------------------------------------------
        # 3. Construct KPI Card Data
        # -------------------------------------------------------------
        kpi_total_income = KPICardWithComparison(
            current_value=round(total_curr_rev, 2),
            previous_value=round(total_prev_rev, 2),
            percentage_change=self._calc_pct_change(total_curr_rev, total_prev_rev),
            comparison_label=comp_label,
        )

        kpi_online_revenue = KPICardWithComparison(
            current_value=round(online_curr_rev, 2),
            previous_value=round(online_prev_rev, 2),
            percentage_change=self._calc_pct_change(online_curr_rev, online_prev_rev),
            comparison_label=comp_label,
        )

        kpi_offline_revenue = KPICardWithComparison(
            current_value=round(offline_curr_rev, 2),
            previous_value=round(offline_prev_rev, 2),
            percentage_change=self._calc_pct_change(offline_curr_rev, offline_prev_rev),
            comparison_label=comp_label,
        )

        kpi_aov = KPICardWithComparison(
            current_value=curr_aov,
            previous_value=prev_aov,
            percentage_change=self._calc_pct_change(curr_aov, prev_aov),
            comparison_label=comp_label,
        )

        # -------------------------------------------------------------
        # 4. Revenue by Source Breakdown
        # -------------------------------------------------------------
        if total_curr_rev > 0:
            online_pct = round((online_curr_rev / total_curr_rev) * 100, 1)
            offline_pct = round((offline_curr_rev / total_curr_rev) * 100, 1)
        else:
            online_pct = 0.0
            offline_pct = 0.0

        source_breakdown = RevenueBySource(
            online_revenue=round(online_curr_rev, 2),
            online_percentage=online_pct,
            offline_revenue=round(offline_curr_rev, 2),
            offline_percentage=offline_pct,
        )

        # -------------------------------------------------------------
        # 5. Revenue by Payment Method
        # -------------------------------------------------------------
        payment_methods_map: Dict[str, float] = {}

        # Online order payment methods
        online_pm_res = await self.db.execute(
            select(Order.payment_method, func.sum(Order.total)).where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                Order.status.in_(valid_order_statuses),
            ).group_by(Order.payment_method)
        )
        for pm, p_sum in online_pm_res.all():
            method_key = pm.strip() if pm else "UPI"
            payment_methods_map[method_key] = payment_methods_map.get(method_key, 0.0) + float(p_sum or 0.0)

        # Offline sale payment methods
        offline_pm_res = await self.db.execute(
            select(OfflineSale.payment_method, func.sum(OfflineSale.total_price)).where(
                OfflineSale.created_at >= curr_start,
                OfflineSale.created_at <= curr_end,
            ).group_by(OfflineSale.payment_method)
        )
        for pm, p_sum in offline_pm_res.all():
            method_key = pm.strip() if pm else "Cash"
            payment_methods_map[method_key] = payment_methods_map.get(method_key, 0.0) + float(p_sum or 0.0)

        pm_list: List[PaymentMethodRevenue] = []
        for pm_name, amount in payment_methods_map.items():
            pm_pct = round((amount / total_curr_rev * 100), 1) if total_curr_rev > 0 else 0.0
            pm_list.append(
                PaymentMethodRevenue(
                    method=pm_name,
                    amount=round(amount, 2),
                    percentage=pm_pct,
                )
            )
        pm_list.sort(key=lambda x: x.amount, reverse=True)

        # -------------------------------------------------------------
        # 6. Time Series Trend & Summary Table Rows
        # -------------------------------------------------------------
        # Group data day-by-day between curr_start and curr_end
        online_orders_raw = await self.db.execute(
            select(Order.total, Order.created_at).where(
                Order.created_at >= curr_start,
                Order.created_at <= curr_end,
                Order.status.in_(valid_order_statuses),
            )
        )
        online_orders_data = online_orders_raw.all()

        offline_sales_raw = await self.db.execute(
            select(OfflineSale.total_price, OfflineSale.created_at).where(
                OfflineSale.created_at >= curr_start,
                OfflineSale.created_at <= curr_end,
            )
        )
        offline_sales_data = offline_sales_raw.all()

        # Bucket by YYYY-MM-DD
        days_map: Dict[str, Dict[str, float]] = {}
        delta_days = (curr_end - curr_start).days + 1
        
        # Cap interval slots between 5 and 31 slots for clean visualization
        step_days = max(1, delta_days // 15) if delta_days > 15 else 1

        curr = curr_start
        while curr <= curr_end:
            d_str = curr.strftime("%Y-%m-%d")
            days_map[d_str] = {
                "online_rev": 0.0,
                "online_cnt": 0,
                "offline_rev": 0.0,
                "offline_cnt": 0,
            }
            curr += timedelta(days=1)

        for total, dt in online_orders_data:
            d_str = dt.strftime("%Y-%m-%d")
            if d_str in days_map:
                days_map[d_str]["online_rev"] += float(total or 0.0)
                days_map[d_str]["online_cnt"] += 1

        for total_price, dt in offline_sales_data:
            d_str = dt.strftime("%Y-%m-%d")
            if d_str in days_map:
                days_map[d_str]["offline_rev"] += float(total_price or 0.0)
                days_map[d_str]["offline_cnt"] += 1

        revenue_trend: List[RevenueTrendDataPoint] = []
        summary_rows: List[RevenueSummaryRow] = []

        sorted_dates = sorted(days_map.keys())

        for idx, d_str in enumerate(sorted_dates):
            d_info = days_map[d_str]
            on_rev = round(d_info["online_rev"], 2)
            on_cnt = int(d_info["online_cnt"])
            off_rev = round(d_info["offline_rev"], 2)
            off_cnt = int(d_info["offline_cnt"])
            tot_rev = round(on_rev + off_rev, 2)
            tot_cnt = on_cnt + off_cnt
            day_aov = round(tot_rev / tot_cnt, 2) if tot_cnt > 0 else 0.0

            # Convert date to display format (e.g. "1 Aug")
            dt_obj = datetime.strptime(d_str, "%Y-%m-%d")
            date_label = dt_obj.strftime("%d %b")

            # Add to trend points if step matches or first/last
            if idx % step_days == 0 or idx == len(sorted_dates) - 1:
                revenue_trend.append(
                    RevenueTrendDataPoint(
                        date=date_label,
                        online_revenue=on_rev,
                        offline_revenue=off_rev,
                        total_revenue=tot_rev,
                    )
                )

            summary_rows.append(
                RevenueSummaryRow(
                    date=d_str,
                    online_orders=on_cnt,
                    online_revenue=on_rev,
                    offline_sales=off_cnt,
                    offline_revenue=off_rev,
                    total_revenue=tot_rev,
                    avg_order_value=day_aov,
                )
            )

        # Sort summary rows descending by date
        summary_rows.sort(key=lambda r: r.date, reverse=True)

        display_range = f"{curr_start.strftime('%d %b %Y')} - {curr_end.strftime('%d %b %Y')}"

        return SuperadminRevenueResponse(
            preset=preset,
            date_from=curr_start.isoformat(),
            date_to=curr_end.isoformat(),
            display_range=display_range,
            total_income=kpi_total_income,
            online_revenue=kpi_online_revenue,
            offline_revenue=kpi_offline_revenue,
            avg_order_value=kpi_aov,
            revenue_trend=revenue_trend,
            revenue_by_source=source_breakdown,
            revenue_by_payment_method=pm_list,
            summary_rows=summary_rows,
        )

    async def generate_revenue_csv(
        self,
        preset: str = "month",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Generates downloadable CSV text for revenue performance analytics."""
        analytics = await self.get_revenue_analytics(preset, date_from, date_to)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header Metadata
        writer.writerow(["CHOVIQUE LUXURY CHOCOLATES - REVENUE PERFORMANCE REPORT"])
        writer.writerow(["Date Range", analytics.display_range])
        writer.writerow(["Filter Preset", analytics.preset])
        writer.writerow([])

        # KPI Summary Section
        writer.writerow(["KPI SUMMARY"])
        writer.writerow(["Metric", "Current Value (INR)", "Previous Value (INR)", "Pct Change (%)", "Comparison Label"])
        writer.writerow(["Total Income", analytics.total_income.current_value, analytics.total_income.previous_value, analytics.total_income.percentage_change, analytics.total_income.comparison_label])
        writer.writerow(["Online Revenue", analytics.online_revenue.current_value, analytics.online_revenue.previous_value, analytics.online_revenue.percentage_change, analytics.online_revenue.comparison_label])
        writer.writerow(["Offline Revenue", analytics.offline_revenue.current_value, analytics.offline_revenue.previous_value, analytics.offline_revenue.percentage_change, analytics.offline_revenue.comparison_label])
        writer.writerow(["Average Order Value", analytics.avg_order_value.current_value, analytics.avg_order_value.previous_value, analytics.avg_order_value.percentage_change, analytics.avg_order_value.comparison_label])
        writer.writerow([])

        # Payment Methods Section
        writer.writerow(["REVENUE BY PAYMENT METHOD"])
        writer.writerow(["Payment Method", "Amount (INR)", "Percentage (%)"])
        for pm in analytics.revenue_by_payment_method:
            writer.writerow([pm.method, pm.amount, pm.percentage])
        writer.writerow([])

        # Daily Revenue Breakdown Table
        writer.writerow(["DAILY REVENUE BREAKDOWN"])
        writer.writerow(["Date", "Online Orders", "Online Revenue (INR)", "Offline Sales", "Offline Revenue (INR)", "Total Revenue (INR)", "Avg Order Value (INR)"])
        for row in analytics.summary_rows:
            writer.writerow([
                row.date,
                row.online_orders,
                row.online_revenue,
                row.offline_sales,
                row.offline_revenue,
                row.total_revenue,
                row.avg_order_value,
            ])

        return output.getvalue()
