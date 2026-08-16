from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class CoinTransactionResponse(BaseModel):
    id: str
    user_id: str
    order_id: Optional[str] = None
    type: str
    coins: int
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RewardSettingsSchema(BaseModel):
    reward_system_enabled: bool = True
    spend_per_coin: float = 10.0      # ₹10 spent = 1 coin earned
    coins_per_rupee: float = 10.0     # 10 coins = ₹1 discount
    max_redemption_percentage: float = 20.0  # Max 20% of eligible subtotal can be paid with coins


class UserWalletResponse(BaseModel):
    id: str
    user_id: str
    coin_balance: int
    rupee_value: float
    settings: RewardSettingsSchema
    recent_transactions: List[CoinTransactionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CalculateRedemptionRequest(BaseModel):
    subtotal: float
    coupon_discount: float = 0.0
    coins_to_use: int = 0


class CalculateRedemptionResponse(BaseModel):
    user_balance: int
    coins_requested: int
    allowed_coins: int
    coin_discount: float
    max_usable_coins: int
    max_coin_discount: float
    message: str


