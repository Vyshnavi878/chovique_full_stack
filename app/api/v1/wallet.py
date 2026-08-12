from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.wallet import (
    UserWalletResponse,
    CoinTransactionResponse,
    CalculateRedemptionRequest,
    CalculateRedemptionResponse,
)
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet", tags=["Wallet & Rewards"])


@router.get("", response_model=UserWalletResponse, summary="Get current user's wallet balance and reward details")
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.get_user_wallet_details(current_user.id)


@router.get("/transactions", summary="Get transaction history with filtering and pagination")
async def get_transactions(
    type: Optional[str] = Query(None, description="ALL, EARN, REDEEM, ADJUSTMENT"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    offset: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    calc_offset = offset if offset is not None else (page - 1) * limit
    txs = await service.wallet_repo.get_transactions(current_user.id, type_filter=type, limit=limit, offset=calc_offset)
    total = await service.wallet_repo.count_transactions(current_user.id, type_filter=type)
    pages = (total + limit - 1) // limit if limit > 0 else 1
    items = [CoinTransactionResponse.model_validate(t) for t in txs]
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "limit": limit
    }


@router.post("/calculate-redemption", response_model=CalculateRedemptionResponse, summary="Calculate allowed coin redemption for order preview")
async def calculate_redemption(
    payload: CalculateRedemptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.calculate_redemption(
        user_id=current_user.id,
        subtotal=payload.subtotal,
        coupon_discount=payload.coupon_discount,
        coins_requested=payload.coins_to_use,
    )
