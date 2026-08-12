import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.superadmin_overview import SuperadminOverviewResponse
from app.services.superadmin_overview_service import SuperadminOverviewService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/superadmin", tags=["Super Admin Enterprise Control"])


@router.get(
    "/overview",
    response_model=SuperadminOverviewResponse,
    summary="Get Super Admin Enterprise Overview statistics",
)
async def get_superadmin_overview(
    timeframe: Optional[str] = Query(
        "7days",
        description="Timeframe preset: today, 7days, 30days, 3months, 1year",
    ),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_user: User = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticated Super Admin-only endpoint returning business KPIs,
    revenue trends, sales source split, top products, and recent activities.
    Returns HTTP 403 Forbidden for non-superadmin roles.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date.",
        )

    service = SuperadminOverviewService(db)
    return await service.get_overview(
        timeframe=timeframe or "7days",
        start_date=start_date,
        end_date=end_date,
    )
