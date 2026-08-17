from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_optional, get_db
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
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    service = CouponService(db)
    user_id = current_user.id if current_user else None
    return await service.get_available_coupons(user_id)

@router.post(
    "/validate",
    response_model=CouponValidationResponse,
    summary="Validate promo / coupon code",
)
async def validate_coupon(
    payload: CouponValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    service = CouponService(db)
    user_id = current_user.id if current_user else "guest"
    return await service.validate_and_calculate_discount(user_id, payload.code)


