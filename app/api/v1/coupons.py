from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.coupon import CouponValidationRequest, CouponValidationResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.post(
    "/validate",
    response_model=CouponValidationResponse,
    summary="Validate promo / coupon code",
)
async def validate_coupon(
    payload: CouponValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.validate_coupon(payload.code)
