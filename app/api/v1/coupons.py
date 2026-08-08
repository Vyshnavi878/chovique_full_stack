from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.coupon import CouponValidationRequest, CouponValidationResponse, UserCouponResponse
from app.services.coupon_service import CouponService

router = APIRouter(prefix="/coupons", tags=["Coupons"])

@router.get(
    "/available",
    response_model=List[UserCouponResponse],
    summary="Get available coupons for the current user",
)
async def get_available_coupons(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CouponService(db)
    return await service.get_available_coupons(current_user.id)

@router.post(
    "/validate",
    response_model=CouponValidationResponse,
    summary="Validate promo / coupon code",
)
async def validate_coupon(
    payload: CouponValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CouponService(db)
    return await service.validate_and_calculate_discount(current_user.id, payload.code)

