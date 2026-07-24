from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.order import OrderPayload
from app.services.checkout_service import CheckoutService

router = APIRouter(prefix="/checkout", tags=["Checkout"])


@router.post("/initiate", summary="Initiate checkout, validate calculations & create Razorpay Order")
async def initiate_checkout(
    payload: OrderPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = CheckoutService(db)
        return await service.initiate_checkout(current_user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
