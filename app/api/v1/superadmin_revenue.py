from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.superadmin_revenue import SuperadminRevenueResponse
from app.services.superadmin_revenue_service import SuperadminRevenueService

router = APIRouter(prefix="/superadmin/analytics/revenue", tags=["Super Admin Revenue Analytics"])


@router.get(
    "",
    response_model=SuperadminRevenueResponse,
    summary="Get Super Admin Revenue Analytics Data",
)
async def get_superadmin_revenue(
    preset: str = Query("month", description="Filter preset: today, week, month, 3months, year, custom"),
    date_from: Optional[str] = Query(None, description="ISO start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO end date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Get detailed Revenue Analytics performance metrics for Super Admin.
    Strictly requires 'superadmin' role authorization.
    """
    parsed_start = None
    parsed_end = None

    if date_from:
        try:
            parsed_start = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_from format. Use ISO format (YYYY-MM-DD).",
            )

    if date_to:
        try:
            parsed_end = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_to format. Use ISO format (YYYY-MM-DD).",
            )

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be after date_to.",
        )

    service = SuperadminRevenueService(db)
    return await service.get_revenue_analytics(
        preset=preset,
        date_from=parsed_start,
        date_to=parsed_end,
    )


@router.get(
    "/export",
    summary="Export Revenue Analytics as CSV",
)
async def export_superadmin_revenue_csv(
    preset: str = Query("month", description="Filter preset: today, week, month, 3months, year, custom"),
    date_from: Optional[str] = Query(None, description="ISO start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO end date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Generate and download CSV report of Revenue Analytics.
    Strictly requires 'superadmin' role authorization.
    """
    parsed_start = None
    parsed_end = None

    if date_from:
        try:
            parsed_start = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_from format. Use ISO format (YYYY-MM-DD).",
            )

    if date_to:
        try:
            parsed_end = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_to format. Use ISO format (YYYY-MM-DD).",
            )

    service = SuperadminRevenueService(db)
    csv_data = await service.generate_revenue_csv(
        preset=preset,
        date_from=parsed_start,
        date_to=parsed_end,
    )

    filename = f"revenue_analytics_{preset}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
