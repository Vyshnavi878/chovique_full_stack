from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.refund import InitiateRefundPayload, RefundResponseSchema
from app.services.refund_service import RefundService

router = APIRouter(prefix="/refunds", tags=["Refunds"])


@router.post("", response_model=RefundResponseSchema, status_code=status.HTTP_201_CREATED, summary="Initiate full or partial refund (admin only)")
async def initiate_refund(
    payload: InitiateRefundPayload,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = RefundService(db)
        return await service.initiate_refund(payload, performed_by_admin_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/order/{order_id}", response_model=list[RefundResponseSchema], summary="Get refund history for an order")
async def get_order_refunds(
    order_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = RefundService(db)
    return await service.get_order_refunds(order_id)
