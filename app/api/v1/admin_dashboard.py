import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.admin_dashboard import (
    CustomerStatsResponse,
    DashboardSummaryResponse,
    LowStockProductsResponse,
    OrderStatsResponse,
    RecentOrdersResponse,
    RewardCoinStatsResponse,
    SalesChartResponse,
    TopSellingProductsResponse,
)
from app.services.admin_dashboard_service import AdminDashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard Analytics"])


def validate_date_range(start_date: Optional[date], end_date: Optional[date]):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date.",
        )


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get aggregated dashboard KPI summary",
)
async def get_dashboard_summary(
    preset: Optional[str] = Query(None, description="Preset filter: today, 7days, 30days, month, custom"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    service = AdminDashboardService(db)
    return await service.get_dashboard_summary(preset=preset, start_date=start_date, end_date=end_date)


@router.get(
    "/orders",
    response_model=OrderStatsResponse,
    summary="Get aggregated order statistics and status breakdown",
)
async def get_order_stats(
    preset: Optional[str] = Query(None, description="Preset filter: today, 7days, 30days, month, custom"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    service = AdminDashboardService(db)
    return await service.get_order_stats(preset=preset, start_date=start_date, end_date=end_date)


@router.get(
    "/customers",
    response_model=CustomerStatsResponse,
    summary="Get customer growth and active shopper statistics",
)
async def get_customer_stats(
    preset: Optional[str] = Query(None, description="Preset filter: today, 7days, 30days, month, custom"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    service = AdminDashboardService(db)
    return await service.get_customer_stats(preset=preset, start_date=start_date, end_date=end_date)


@router.get(
    "/reward-coins",
    response_model=RewardCoinStatsResponse,
    summary="Get reward coin distribution statistics",
)
async def get_reward_coin_stats(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminDashboardService(db)
    return await service.get_reward_coin_stats()


@router.get(
    "/sales-chart",
    response_model=SalesChartResponse,
    summary="Get sales trend overview points for AreaChart",
)
async def get_sales_chart(
    preset: Optional[str] = Query(None, description="Preset filter: today, 7days, 30days, month, custom"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    service = AdminDashboardService(db)
    return await service.get_sales_chart(preset=preset, start_date=start_date, end_date=end_date)


@router.get(
    "/top-products",
    response_model=TopSellingProductsResponse,
    summary="Get top selling products via SQL aggregation",
)
async def get_top_products(
    limit: int = Query(5, ge=1, le=50, description="Max products to return"),
    preset: Optional[str] = Query(None, description="Preset filter: today, 7days, 30days, month, custom"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    service = AdminDashboardService(db)
    return await service.get_top_products(limit=limit, preset=preset, start_date=start_date, end_date=end_date)


@router.get(
    "/recent-orders",
    response_model=RecentOrdersResponse,
    summary="Get recent orders list",
)
async def get_recent_orders(
    limit: int = Query(5, ge=1, le=50, description="Max orders to return"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminDashboardService(db)
    return await service.get_recent_orders(limit=limit)


@router.get(
    "/low-stock-products",
    response_model=LowStockProductsResponse,
    summary="Get low stock alert products list",
)
async def get_low_stock_products(
    threshold: int = Query(10, ge=1, description="Low stock threshold count"),
    limit: int = Query(10, ge=1, le=50, description="Max items to return"),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminDashboardService(db)
    return await service.get_low_stock_products(threshold=threshold, limit=limit)
