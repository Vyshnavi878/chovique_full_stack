from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.superadmin_sales import (
    OfflineLedgerResponse,
    OnlineLedgerResponse,
    ProductSalesPerformanceResponse,
)
from app.services.superadmin_sales_service import SuperadminSalesService

router = APIRouter(prefix="/superadmin/analytics/sales", tags=["Super Admin Sales Analytics & Ledger"])


def _parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {date_str}. Use ISO format (YYYY-MM-DD).",
        )


@router.get(
    "",
    response_model=ProductSalesPerformanceResponse,
    summary="Get Product Sales Performance & Stock Analytics",
)
async def get_superadmin_sales(
    preset: str = Query("this_month", description="Date preset: today, yesterday, last_7_days, last_30_days, this_month, last_month, custom"),
    search: Optional[str] = Query(None, description="Search product name or category"),
    category: Optional[str] = Query(None, description="Filter category"),
    date_from: Optional[str] = Query(None, description="ISO start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO end date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin")),
):
    """
    Get Product Sales, Order & Stock Performance reporting metrics.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminSalesService(db)
    return await service.get_product_sales_performance(
        preset=preset,
        search=search,
        category=category,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )


@router.get(
    "/online",
    response_model=OnlineLedgerResponse,
    summary="Get Online Sales Ledger",
)
async def get_superadmin_online_sales_ledger(
    preset: Optional[str] = Query(None, description="Date preset: today, yesterday, last_7_days, last_30_days, this_month, last_month, all_time, custom"),
    search: Optional[str] = Query(None, description="Search order ID, customer name or email"),
    status: Optional[str] = Query(None, description="Filter order status (e.g. Paid, Shipped, Delivered, Processing)"),
    payment_method: Optional[str] = Query(None, description="Filter payment method (e.g. UPI, Card, COD)"),
    payment_status_filter: Optional[str] = Query(None, description="Filter by payment status (e.g. Completed, Pending, Cancelled)"),
    date_from: Optional[str] = Query(None, description="ISO start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO end date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin")),
):
    """
    Get paginated Online Sales Ledger records.
    Strictly requires 'superadmin' or 'admin' role authorization.
    """
    parsed_start = _parse_iso_date(date_from) if date_from else None
    parsed_end = _parse_iso_date(date_to) if date_to else None

    service = SuperadminSalesService(db)
    return await service.get_online_sales_ledger(
        preset=preset,
        search=search,
        status_filter=status,
        payment_method=payment_method,
        payment_status_filter=payment_status_filter,
        date_from=parsed_start,
        date_to=parsed_end,
        date_from_iso=date_from,
        date_to_iso=date_to,
        page=page,
        limit=limit,
    )


@router.get(
    "/offline",
    response_model=OfflineLedgerResponse,
    summary="Get Offline Sales Ledger",
)
async def get_superadmin_offline_sales_ledger(
    preset: Optional[str] = Query(None, description="Date preset: today, yesterday, last_7_days, last_30_days, this_month, last_month, all_time, custom"),
    search: Optional[str] = Query(None, description="Search receipt ID or product name"),
    payment_method: Optional[str] = Query(None, description="Filter payment method (e.g. Cash, UPI, Card)"),
    date_from: Optional[str] = Query(None, description="ISO start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO end date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin")),
):
    """
    Get paginated Offline Sales Ledger records.
    Strictly requires 'superadmin' or 'admin' role authorization.
    """
    parsed_start = _parse_iso_date(date_from) if date_from else None
    parsed_end = _parse_iso_date(date_to) if date_to else None

    service = SuperadminSalesService(db)
    return await service.get_offline_sales_ledger(
        preset=preset,
        search=search,
        payment_method=payment_method,
        date_from=parsed_start,
        date_to=parsed_end,
        date_from_iso=date_from,
        date_to_iso=date_to,
        page=page,
        limit=limit,
    )


@router.get(
    "/export",
    summary="Export Sales Analytics or Ledger as CSV",
)
async def export_superadmin_sales_csv(
    tab: str = Query("products", description="Tab to export: products, online, offline"),
    preset: str = Query("this_month", description="Preset date range"),
    search: Optional[str] = Query(None, description="Search filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    date_from: Optional[str] = Query(None, description="ISO start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO end date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin")),
):
    """
    Generate downloadable CSV export for Sales Analytics & Ledgers.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminSalesService(db)
    csv_data = await service.generate_sales_csv(
        tab=tab,
        preset=preset,
        search=search,
        category=category,
        date_from=date_from,
        date_to=date_to,
    )

    filename = f"sales_analytics_{tab}_{preset}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
