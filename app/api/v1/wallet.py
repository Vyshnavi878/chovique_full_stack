from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
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


@router.get("/transactions", response_model=List[CoinTransactionResponse], summary="Get transaction history")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    txs = await service.wallet_repo.get_transactions(current_user.id, limit=limit, offset=offset)
    return [CoinTransactionResponse.model_validate(t) for t in txs]


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
