import json
import logging
import math
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.wallet_repository import WalletRepository
from app.repositories.site_config_repository import SiteConfigRepository
from app.schemas.wallet import (
    RewardSettingsSchema,
    UserWalletResponse,
    CoinTransactionResponse,
    CalculateRedemptionResponse,
)

logger = logging.getLogger(__name__)

DEFAULT_REWARD_SETTINGS = {
    "reward_system_enabled": True,
    "spend_per_coin": 10.0,
    "coins_per_rupee": 10.0,
    "max_redemption_percentage": 20.0,
    "welcome_coins": 50,
    "first_order_coins": 100,
    "per_order_coins_fixed": 0,
}


class WalletService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.site_config_repo = SiteConfigRepository(db)

    async def get_reward_settings(self) -> RewardSettingsSchema:
        raw = await self.site_config_repo.get("reward_settings")
        if not raw:
            return RewardSettingsSchema(**DEFAULT_REWARD_SETTINGS)

        try:
            if isinstance(raw, str):
                data = json.loads(raw)
            elif isinstance(raw, dict):
                data = raw
            else:
                data = DEFAULT_REWARD_SETTINGS
            merged = {**DEFAULT_REWARD_SETTINGS, **data}
            return RewardSettingsSchema(**merged)
        except Exception as e:
            logger.error(f"Error parsing reward settings: {e}")
            return RewardSettingsSchema(**DEFAULT_REWARD_SETTINGS)

    async def update_reward_settings(self, settings: RewardSettingsSchema) -> RewardSettingsSchema:
        dump = settings.model_dump()
        await self.site_config_repo.set("reward_settings", dump)
        return settings

    async def get_user_wallet_details(self, user_id: str) -> UserWalletResponse:
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        settings = await self.get_reward_settings()
        transactions = await self.wallet_repo.get_transactions(user_id, limit=20)

        rupee_val = round(wallet.coin_balance / settings.coins_per_rupee, 2) if settings.coins_per_rupee > 0 else 0.0

        return UserWalletResponse(
            id=wallet.id,
            user_id=wallet.user_id,
            coin_balance=wallet.coin_balance,
            rupee_value=rupee_val,
            settings=settings,
            recent_transactions=[CoinTransactionResponse.model_validate(t) for t in transactions],
        )

    async def calculate_redemption(
        self,
        user_id: str,
        subtotal: float,
        coupon_discount: float = 0.0,
        coins_requested: int = 0,
    ) -> CalculateRedemptionResponse:
        settings = await self.get_reward_settings()
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)

        if not settings.reward_system_enabled:
            return CalculateRedemptionResponse(
                user_balance=wallet.coin_balance,
                coins_requested=coins_requested,
                allowed_coins=0,
                coin_discount=0.0,
                max_usable_coins=0,
                max_coin_discount=0.0,
                message="Reward system is currently disabled.",
            )

        eligible_subtotal = max(0.0, subtotal - coupon_discount)
        max_discount_allowed = eligible_subtotal * (settings.max_redemption_percentage / 100.0)
        max_usable_coins = math.floor(max_discount_allowed * settings.coins_per_rupee)

        # Cap coins by balance and allowed threshold
        allowed_coins = min(wallet.coin_balance, coins_requested, max_usable_coins)
        if allowed_coins < 0:
            allowed_coins = 0

        coin_discount = round(allowed_coins / settings.coins_per_rupee, 2) if settings.coins_per_rupee > 0 else 0.0

        if allowed_coins <= 0:
            if wallet.coin_balance <= 0:
                msg = "Available reward coins are insufficient for redemption on this order."
            elif max_usable_coins <= 0:
                msg = "Reward coins cannot be applied to this order."
            elif wallet.coin_balance < coins_requested:
                msg = f"Requested {coins_requested} coins, but available balance is {wallet.coin_balance} coins."
            else:
                msg = "Available reward coins are insufficient for redemption on this order."
        else:
            msg = f"{allowed_coins} coins applied for Rs. {coin_discount} discount."
            if coins_requested > allowed_coins:
                if wallet.coin_balance < coins_requested:
                    msg = f"Requested {coins_requested} coins, but available balance is {wallet.coin_balance} coins."
                else:
                    msg = f"Maximum allowed coins for this order is {max_usable_coins} ({settings.max_redemption_percentage}% of order value)."

        return CalculateRedemptionResponse(
            user_balance=wallet.coin_balance,
            coins_requested=coins_requested,
            allowed_coins=allowed_coins,
            coin_discount=coin_discount,
            max_usable_coins=max_usable_coins,
            max_coin_discount=round(max_discount_allowed, 2),
            message=msg,
        )

    async def redeem_coins(
        self,
        user_id: str,
        order_id: str,
        coins: int,
        commit: bool = False,
    ):
        if coins <= 0:
            return None
        tx = await self.wallet_repo.add_transaction(
            user_id=user_id,
            transaction_type="REDEEM",
            coins=-abs(coins),
            description=f"Redeemed on Order #{order_id}",
            order_id=order_id,
            commit=commit,
        )

        try:
            from app.repositories.notification_repository import NotificationRepository
            notif_repo = NotificationRepository(self.db)
            await notif_repo.create(
                user_id=user_id,
                type="reward",
                title="Reward Coins Redeemed",
                message=f"You redeemed {abs(coins)} Reward Coins on your order.",
                text=f"You redeemed {abs(coins)} Reward Coins on your order.",
                related_entity_type="wallet",
                related_entity_id=order_id,
                reference_id=order_id,
                commit=commit,
            )
        except Exception as err:
            logger.debug(f"Failed to create coin redeemed notification: {err}")

        return tx

    async def earn_coins(
        self,
        user_id: str,
        order_id: str,
        payable_amount: float,
        commit: bool = False,
    ):
        settings = await self.get_reward_settings()
        if not settings.reward_system_enabled:
            return 0, None

        # Check if first order
        from app.models.order import Order
        from sqlalchemy import select, func
        order_count = await self.db.scalar(
            select(func.count(Order.id)).where(Order.user_id == user_id, Order.status != "CANCELLED")
        )

        coins_earned = 0
        desc = f"Earned from Order #{order_id}"

        # If it's the very first order being processed
        if order_count <= 1:
            coins_earned = settings.first_order_coins
            desc = f"Bonus for First Order #{order_id}"
        else:
            if settings.per_order_coins_fixed > 0:
                coins_earned = settings.per_order_coins_fixed
            elif settings.spend_per_coin > 0:
                coins_earned = math.floor(payable_amount / settings.spend_per_coin)

        if coins_earned <= 0:
            return 0, None

        tx = await self.wallet_repo.add_transaction(
            user_id=user_id,
            transaction_type="EARN",
            coins=coins_earned,
            description=desc,
            order_id=order_id,
            commit=commit,
        )

        try:
            from app.repositories.notification_repository import NotificationRepository
            notif_repo = NotificationRepository(self.db)
            await notif_repo.create(
                user_id=user_id,
                type="reward",
                title="Reward Coins Earned",
                message=f"You earned {coins_earned} Reward Coins from your order.",
                text=f"You earned {coins_earned} Reward Coins from your order.",
                related_entity_type="wallet",
                related_entity_id=order_id,
                reference_id=order_id,
                commit=commit,
            )
        except Exception as err:
            logger.debug(f"Failed to create coin earned notification: {err}")

        return coins_earned, tx

    async def refund_order_coins(
        self,
        user_id: str,
        order_id: str,
        coins_used: int,
        coins_earned: int,
        commit: bool = False,
    ):
        # Prevent double refund
        existing = await self.wallet_repo.get_order_transactions(order_id)
        has_refund = any(t.type == "REFUND" for t in existing)
        if has_refund:
            return

        # Restore redeemed coins
        if coins_used > 0:
            await self.wallet_repo.add_transaction(
                user_id=user_id,
                transaction_type="REFUND",
                coins=coins_used,
                description=f"Refunded from Cancelled Order #{order_id}",
                order_id=order_id,
                commit=commit,
            )

        # Reverse earned coins
        if coins_earned > 0:
            await self.wallet_repo.add_transaction(
                user_id=user_id,
                transaction_type="ADJUSTMENT",
                coins=-coins_earned,
                description=f"Reversed earned coins from Cancelled Order #{order_id}",
                order_id=order_id,
                commit=commit,
            )


