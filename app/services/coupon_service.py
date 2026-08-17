import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.coupon import Coupon, CouponUsage, CouponEligibilityRule, CouponCategory, CouponProduct
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
            # 1. Coupon Type check: ONLY Customer Coupons are visible in customer available-coupons list
            # Influencer Coupons MUST NOT appear in the customer available coupons list/API
            coupon_type = str(getattr(c, "coupon_type", "CUSTOMER") or "CUSTOMER").strip().upper()
            if coupon_type not in ["CUSTOMER", "CUSTOMER_COUPON", "CUSTOMER COUPON"]:
                continue

            # 2. Check user-specific usage limit (Per-user usage tracking)
            user_usage = 0
            if c.per_user_usage_limit > 0:
                user_usage_q = select(func.count(CouponUsage.id)).where(
                    CouponUsage.coupon_id == c.id,
                    CouponUsage.user_id == user_id
                )
                user_usage = (await self.db.execute(user_usage_q)).scalar() or 0

            # 3. Check total usage limit
            total_usage = 0
            if c.usage_limit > 0:
                total_usage_q = select(func.count(CouponUsage.id)).where(
                    CouponUsage.coupon_id == c.id
                )
                total_usage = (await self.db.execute(total_usage_q)).scalar() or 0

            # 4. Dates & Active checks
            is_active_flag = bool(getattr(c, "is_active", True))
            start_dt = (c.start_at if c.start_at.tzinfo else c.start_at.replace(tzinfo=timezone.utc)) if c.start_at else None
            exp_dt = (c.expires_at if c.expires_at.tzinfo else c.expires_at.replace(tzinfo=timezone.utc)) if c.expires_at else None

            is_started = (start_dt <= now_utc) if start_dt else True
            is_not_expired = (exp_dt > now_utc) if exp_dt else True
            is_total_available = (total_usage < c.usage_limit) if c.usage_limit > 0 else True
            is_user_available = (user_usage < c.per_user_usage_limit) if c.per_user_usage_limit > 0 else True

            # Determine dynamic status: Available / Used / Expired / Not Available
            if not is_user_available:
                status_str = "Used"
                is_active = False
            elif not is_started:
                status_str = "Not Available"
                is_active = False
            elif not is_not_expired or not is_active_flag or not is_total_available:
                status_str = "Expired"
                is_active = False
            else:
                status_str = "Available"
                is_active = True

            # Check eligibility rules for inclusion (e.g. FIRST_ORDER, SPECIFIC_USERS)
            if hasattr(c, "eligibility_rule") and c.eligibility_rule == "SPECIFIC_USERS":
                if c.eligibility_value and str(user_id) not in c.eligibility_value.split(","):
                    continue

            exp_str = c.expires_at.strftime("%Y-%m-%d") if c.expires_at else None
            start_str = c.start_at.strftime("%Y-%m-%d") if c.start_at else None

            resp = UserCouponResponse(
                id=c.id,
                code=c.code,
                name=c.name or c.code,
                description=c.description or "",
                coupon_type="CUSTOMER",
                discount_type=c.discount_type or "PERCENTAGE",
                discount_percent=c.discount_percent or 0.0,
                discount_amount=c.discount_amount or 0.0,
                maximum_discount_amount=c.maximum_discount_amount or 0.0,
                minimum_order_amount=c.minimum_order_amount or 0.0,
                start_at=c.start_at,
                expires_at=c.expires_at,
                startDate=start_str,
                expiryDate=exp_str,
                start_date=start_str,
                expiry_date=exp_str,
                expiresAt=exp_str,
                startAt=start_str,
                is_active=is_active,
                status=status_str,
            )
            result.append(resp)

        seen_codes = set()
        deduped = []
        for r in result:
            code_key = r.code.upper()
            if code_key not in seen_codes:
                seen_codes.add(code_key)
                deduped.append(r)
        return deduped

    async def validate_and_calculate_discount(self, user_id: str, code: str) -> CouponValidationResponse:
        coupon = await self.coupon_repo.get_by_code(code)
        if not coupon:
            return CouponValidationResponse(valid=False, code=code, message="Invalid or expired promo code.")

        now_utc = datetime.now(timezone.utc)
        if not coupon.is_active:
            return CouponValidationResponse(valid=False, code=code, message="Invalid or expired promo code.")
            
        if coupon.start_at:
            start_dt = coupon.start_at if coupon.start_at.tzinfo else coupon.start_at.replace(tzinfo=timezone.utc)
            if start_dt > now_utc:
                return CouponValidationResponse(valid=False, code=code, message="Invalid or expired promo code.")
            
        if coupon.expires_at:
            exp_dt = coupon.expires_at if coupon.expires_at.tzinfo else coupon.expires_at.replace(tzinfo=timezone.utc)
            if exp_dt <= now_utc:
                return CouponValidationResponse(valid=False, code=code, message="Invalid or expired promo code.")
            
        # Check total usage limit
        if coupon.usage_limit > 0:
            total_usage_q = select(func.count(CouponUsage.id)).where(CouponUsage.coupon_id == coupon.id)
            total_usage = (await self.db.execute(total_usage_q)).scalar() or 0
            if total_usage >= coupon.usage_limit:
                return CouponValidationResponse(valid=False, code=code, message="Promo code usage limit reached.")
                
        # Check per-user usage limit
        if coupon.per_user_usage_limit > 0:
            user_usage_q = select(func.count(CouponUsage.id)).where(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == user_id)
            user_usage = (await self.db.execute(user_usage_q)).scalar() or 0
            if user_usage >= coupon.per_user_usage_limit:
                return CouponValidationResponse(valid=False, code=code, message="You have already used this promo code.")

        # Check Eligibility rules
        rules_q = select(CouponEligibilityRule).where(CouponEligibilityRule.coupon_id == coupon.id)
        rules = (await self.db.scalars(rules_q)).all()
        
        for rule in rules:
            if rule.rule_type == "FIRST_ORDER":
                user_orders_q = select(func.count(Order.id)).where(Order.user_id == user_id, Order.status != "Cancelled")
                order_count = (await self.db.execute(user_orders_q)).scalar() or 0
                if order_count > 0:
                    return CouponValidationResponse(valid=False, code=code, message="This promo code is only for first-time orders.")
            elif rule.rule_type == "SPECIFIC_USERS" and rule.rule_value:
                allowed_users = [u.strip() for u in rule.rule_value.split(",") if u.strip()]
                if str(user_id) not in allowed_users:
                    return CouponValidationResponse(valid=False, code=code, message="This promo code is not valid for your account.")

        # Get Cart to calculate discount
        cart = await self.cart_repo.get_or_create_user_cart(user_id)
        
        # Check Product/Category Restrictions (Applicability: Entire Store vs Specific Products vs Specific Categories)
        coupon_categories_q = select(CouponCategory.category_id).where(CouponCategory.coupon_id == coupon.id)
        coupon_categories = (await self.db.scalars(coupon_categories_q)).all()
        allowed_category_ids = set(str(cid).strip() for cid in coupon_categories if cid)
        
        coupon_products_q = select(CouponProduct.product_id).where(CouponProduct.coupon_id == coupon.id)
        coupon_products = (await self.db.scalars(coupon_products_q)).all()
        allowed_product_ids = set(str(pid).strip() for pid in coupon_products if pid)

        # Calculate subtotal (eligible vs total)
        total_subtotal = 0.0
        eligible_subtotal = 0.0
        
        cart_items = cart.items if (cart and cart.items) else []
        for item in cart_items:
            prod = item.product
            item_price = (prod.price or 0.0) * item.quantity
            total_subtotal += item_price
            
            is_eligible = True
            if allowed_product_ids:
                prod_matched = (
                    str(item.product_id) in allowed_product_ids
                    or (prod and str(prod.id) in allowed_product_ids)
                    or (prod and prod.sku and str(prod.sku).strip() in allowed_product_ids)
                    or (prod and prod.slug and str(prod.slug).strip() in allowed_product_ids)
                    or (prod and prod.name and str(prod.name).strip().lower() in [p.lower() for p in allowed_product_ids])
                )
                if not prod_matched:
                    is_eligible = False

            if allowed_category_ids:
                cat_matched = False
                if prod:
                    if prod.category_id and str(prod.category_id) in allowed_category_ids:
                        cat_matched = True
                    elif prod.category and str(prod.category).lower() in [c.lower() for c in allowed_category_ids]:
                        cat_matched = True
                    elif prod.category_rel:
                        if str(prod.category_rel.id) in allowed_category_ids or str(prod.category_rel.name).lower() in [c.lower() for c in allowed_category_ids]:
                            cat_matched = True
                if not cat_matched:
                    is_eligible = False
                
            if is_eligible:
                eligible_subtotal += item_price

        if len(cart_items) > 0 and (allowed_category_ids or allowed_product_ids) and eligible_subtotal == 0.0:
            return CouponValidationResponse(valid=False, code=code, message="This promo code is only applicable to specific items which are not in your cart.")

        if coupon.minimum_order_amount > 0 and eligible_subtotal > 0 and eligible_subtotal < coupon.minimum_order_amount:
            return CouponValidationResponse(valid=False, code=code, message=f"Minimum eligible order amount of ₹{coupon.minimum_order_amount} required.")
            
        # Calculate Discount based on eligible_subtotal
        calculated = 0.0
        if coupon.discount_type == "PERCENTAGE":
            calculated = (eligible_subtotal * coupon.discount_percent) / 100.0
            if coupon.maximum_discount_amount > 0:
                calculated = min(calculated, coupon.maximum_discount_amount)
        elif coupon.discount_type == "FIXED_AMOUNT":
            calculated = min(coupon.discount_amount, eligible_subtotal) if eligible_subtotal > 0 else coupon.discount_amount
        elif coupon.discount_type == "FREE_SHIPPING":
            calculated = 50.0
            
        return CouponValidationResponse(
            valid=True,
            code=coupon.code,
            discount_type=coupon.discount_type,
            discount_percent=coupon.discount_percent,
            discount_amount=coupon.discount_amount,
            calculated_discount=round(calculated, 2),
            message=f"Promo code {coupon.code} applied successfully!"
        )
