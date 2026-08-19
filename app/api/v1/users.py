from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.address_repository import AddressRepository
from app.schemas.user import UserResponse, AddressSchema

router = APIRouter( prefix="/users", tags=["Users"],)


# ======================================================
# GET CURRENT USER
# ======================================================

@router.get( "/me",response_model=UserResponse,)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch addresses explicitly instead of accessing current_user.addresses,
    # which lazy-loads outside an awaited context under async SQLAlchemy and
    # raises sqlalchemy.exc.MissingGreenlet.
    addresses = await AddressRepository(db).get_user_addresses(current_user.id)
    default_address = next(
        (addr for addr in addresses if addr.is_default),
        None,
    )

    user = UserResponse.from_orm_user(current_user)

    if default_address:
        user.profile.address = AddressSchema(
            street=default_address.street,
            city=default_address.city,
            state=default_address.state,
            zip=default_address.zip,
        )

    return user

from app.schemas.coupon import UserCouponResponse
from app.services.coupon_service import CouponService

@router.get("/me/coupons", response_model=list[UserCouponResponse], summary="Get available coupons for current user")
async def get_my_user_coupons(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.get_user_coupons(current_user.id)


@router.get("/me/coupons/used", summary="Get used coupons for current user")
async def get_my_used_coupons(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CouponService(db)
    return await service.get_used_coupons(current_user.id)