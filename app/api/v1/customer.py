from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.coupon import UserCouponResponse
from app.schemas.user import (
    AvatarUploadResponse,
    CustomerAddressCreate,
    CustomerAddressResponse,
    ProfileUpdatePayload,
    SupportNotificationResponse,
    UserResponse,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/users/me", tags=["Customer Dashboard"])


# ======================================================
# Profile Management
# ======================================================

@router.patch(
    "",
    response_model=UserResponse,
    summary="Update authenticated user profile",
)
async def update_profile(
    payload: ProfileUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.update_profile(current_user.id, payload)


@router.post(
    "/avatar",
    response_model=AvatarUploadResponse,
    summary="Upload user avatar image",
)
@router.put(
    "/avatar",
    response_model=AvatarUploadResponse,
    summary="Update user avatar image",
)
@router.patch(
    "/avatar",
    response_model=AvatarUploadResponse,
    summary="Update user avatar image",
)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.upload_avatar(current_user.id, avatar)


# ======================================================
# Customer Addresses
# ======================================================

@router.get(
    "/addresses",
    response_model=list[CustomerAddressResponse],
    summary="Get authenticated user's saved addresses",
)
async def get_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.get_addresses(current_user.id)


@router.post(
    "/addresses",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new saved address",
)
async def add_address(
    payload: CustomerAddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.add_address(current_user.id, payload)


@router.delete(
    "/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved address",
)
async def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    deleted = await service.delete_address(current_user.id, address_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")


@router.patch(
    "/addresses/{address_id}/default",
    response_model=CustomerAddressResponse,
    summary="Set an address as default",
)
async def set_default_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    addr = await service.set_default_address(current_user.id, address_id)
    if not addr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")
    return addr


# ======================================================
# User Coupons
# ======================================================

@router.get(
    "/coupons",
    response_model=list[UserCouponResponse],
    summary="Get available coupons for authenticated user",
)
async def get_my_coupons(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.get_user_coupons(current_user.id)


# ======================================================
# Notifications
# ======================================================

@router.get(
    "/notifications",
    response_model=list[SupportNotificationResponse],
    summary="Get notifications for authenticated user",
)
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.get_user_notifications(current_user.id)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=SupportNotificationResponse,
    summary="Mark notification as read",
)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    notif = await service.mark_notification_read(current_user.id, notification_id)
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return notif


@router.delete(
    "/notifications/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    await service.delete_notification(current_user.id, notification_id)
    return None

