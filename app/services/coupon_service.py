import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.coupon import Coupon, CouponUsage, CouponEligibilityRule
from app.models.order import Order
from app.repositories.coupon_repository import CouponRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.coupon import CouponValidationResponse, UserCouponResponse
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

class CouponService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.coupon_repo = CouponRepository(db)
        self.cart_repo = CartRepository(db)
        self.order_repo = OrderRepository(db)

    async def get_available_coupons(self, user_id: str) -> list[UserCouponResponse]:
        coupons = await self.coupon_repo.get_all()
        now_utc = datetime.now(timezone.utc)

        result = []
        for c in coupons:
            # 1. Active status check
            is_active_flag = getattr(c, "is_active", True)
            if not is_active_flag:
                continue

            # 2. Start date check
            if c.start_at:
                start_dt = c.start_at if c.start_at.tzinfo else c.start_at.replace(tzinfo=timezone.utc)
                if start_dt > now_utc:
                    continue

            # 3. Expiry date check
            if c.expires_at:
                exp_dt = c.expires_at if c.expires_at.tzinfo else c.expires_at.replace(tzinfo=timezone.utc)
                if exp_dt <= now_utc:
                    continue

            # 4. Check specific user eligibility if configured
            if hasattr(c, "eligibility_rule") and c.eligibility_rule == "SPECIFIC_USERS":
                if c.eligibility_value and str(user_id) not in c.eligibility_value.split(","):
                    continue

            # 5. Check per-user usage limit (USED COUPONS MUST NOT APPEAR AGAIN)
            if c.per_user_usage_limit > 0:
                user_usage_q = select(func.count(CouponUsage.id)).where(
                    CouponUsage.coupon_id == c.id,
                    CouponUsage.user_id == user_id
                )
                user_usage = (await self.db.execute(user_usage_q)).scalar() or 0
                if user_usage >= c.per_user_usage_limit:
                    continue

            # 6. Check total usage limit
            if c.usage_limit > 0:
                total_usage_q = select(func.count(CouponUsage.id)).where(
                    CouponUsage.coupon_id == c.id
                )
                total_usage = (await self.db.execute(total_usage_q)).scalar() or 0
                if total_usage >= c.usage_limit:
                    continue

            # 7. Check eligibility rules (e.g. FIRST_ORDER)
            rules_q = select(CouponEligibilityRule).where(CouponEligibilityRule.coupon_id == c.id)
            rules = (await self.db.scalars(rules_q)).all()
            ineligible = False
            for rule in rules:
                if rule.rule_type == "FIRST_ORDER":
                    user_orders_q = select(func.count(Order.id)).where(
                        Order.user_id == user_id, Order.status != "Cancelled"
                    )
                    order_count = (await self.db.execute(user_orders_q)).scalar() or 0
                    if order_count > 0:
                        ineligible = True
                        break
            if ineligible:
                continue

            resp = UserCouponResponse(
                id=c.id,
                code=c.code,
                name=c.name or c.code,
                description=c.description or "",
                discount_type=c.discount_type or "PERCENTAGE",
                discount_percent=c.discount_percent or 0.0,
                discount_amount=c.discount_amount or 0.0,
                maximum_discount_amount=c.maximum_discount_amount or 0.0,
                minimum_order_amount=c.minimum_order_amount or 0.0,
                start_at=c.start_at,
                expires_at=c.expires_at,
                is_active=True,
                status="ACTIVE",
            )
            result.append(resp)

        return result

    async def validate_and_calculate_discount(self, user_id: str, code: str) -> CouponValidationResponse:
        coupon = await self.coupon_repo.get_by_code(code)
        if not coupon:
            return CouponValidationResponse(valid=False, code=code, message="Invalid or expired promo code.")

        now_utc = datetime.now(timezone.utc)
        if not coupon.is_active:
            return CouponValidationResponse(valid=False, code=code, message="Promo code is inactive.")
            
        if coupon.start_at and coupon.start_at > now_utc:
            return CouponValidationResponse(valid=False, code=code, message="Promo code is not yet active.")
            
        if coupon.expires_at and coupon.expires_at <= now_utc:
            return CouponValidationResponse(valid=False, code=code, message="Promo code has expired.")
            
        # Check usage limits
        if coupon.usage_limit > 0:
            total_usage_q = select(func.count(CouponUsage.id)).where(CouponUsage.coupon_id == coupon.id)
            total_usage = (await self.db.execute(total_usage_q)).scalar()
            if total_usage >= coupon.usage_limit:
                return CouponValidationResponse(valid=False, code=code, message="Promo code usage limit reached.")
                
        if coupon.per_user_usage_limit > 0:
            user_usage_q = select(func.count(CouponUsage.id)).where(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == user_id)
            user_usage = (await self.db.execute(user_usage_q)).scalar()
            if user_usage >= coupon.per_user_usage_limit:
                return CouponValidationResponse(valid=False, code=code, message="You have already used this promo code.")

        # Check Eligibility
        # Assume rules are eagerly loaded or we load them
        rules_q = select(CouponEligibilityRule).where(CouponEligibilityRule.coupon_id == coupon.id)
        rules = (await self.db.scalars(rules_q)).all()
        
        for rule in rules:
            if rule.rule_type == "FIRST_ORDER":
                user_orders_q = select(func.count(Order.id)).where(Order.user_id == user_id, Order.status != "Cancelled")
                order_count = (await self.db.execute(user_orders_q)).scalar()
                if order_count > 0:
                    return CouponValidationResponse(valid=False, code=code, message="This promo code is only for first-time orders.")
            
            # Additional rules can be implemented here (INACTIVE_CUSTOMER, MIN_LIFETIME_SPEND)

        # Get Cart to calculate discount
        cart = await self.cart_repo.get_or_create_user_cart(user_id)
        
        # Calculate subtotal
        subtotal = sum(item.product.price * item.quantity for item in cart.items)
        
        if coupon.minimum_order_amount > 0 and subtotal < coupon.minimum_order_amount:
            return CouponValidationResponse(valid=False, code=code, message=f"Minimum order amount of ₹{coupon.minimum_order_amount} required.")
            
        # Calculate Discount
        calculated = 0.0
        if coupon.discount_type == "PERCENTAGE":
            calculated = (subtotal * coupon.discount_percent) / 100.0
            if coupon.maximum_discount_amount > 0:
                calculated = min(calculated, coupon.maximum_discount_amount)
        elif coupon.discount_type == "FIXED_AMOUNT":
            calculated = min(coupon.discount_amount, subtotal)
        elif coupon.discount_type == "FREE_SHIPPING":
            calculated = 99.0 # Assuming shipping is 99
            
        return CouponValidationResponse(
            valid=True,
            code=coupon.code,
            discount_type=coupon.discount_type,
            discount_percent=coupon.discount_percent,
            discount_amount=coupon.discount_amount,
            calculated_discount=round(calculated, 2),
            message=f"Promo code {coupon.code} applied successfully!"
        )
