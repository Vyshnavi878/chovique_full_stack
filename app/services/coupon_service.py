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

    async def _get_coupon_user_usage(self, coupon: Coupon, user_id: str | None) -> int:
        if not user_id or user_id == "guest":
            return 0

        code_upper = (coupon.code or "").strip().upper()

        # 1. Count from CouponUsage relation (joining Coupon and outerjoining Order to exclude cancelled)
        cu_q = (
            select(func.count(CouponUsage.id))
            .join(Coupon, CouponUsage.coupon_id == Coupon.id)
            .outerjoin(Order, CouponUsage.order_id == Order.id)
            .where(
                or_(CouponUsage.coupon_id == coupon.id, func.upper(func.trim(Coupon.code)) == code_upper),
                CouponUsage.user_id == user_id,
                or_(Order.id.is_(None), Order.status.notin_(["Cancelled", "CANCELLED"]))
            )
        )
        cu_cnt = (await self.db.execute(cu_q)).scalar() or 0

        # 2. Count from Order table directly for matching coupon_code (excluding cancelled)
        ord_q = (
            select(func.count(Order.id))
            .where(
                Order.user_id == user_id,
                func.upper(func.trim(Order.coupon_code)) == code_upper,
                Order.status.notin_(["Cancelled", "CANCELLED"])
            )
        )
        ord_cnt = (await self.db.execute(ord_q)).scalar() or 0

        return max(cu_cnt, ord_cnt)

    async def _get_coupon_total_usage(self, coupon: Coupon) -> int:
        code_upper = (coupon.code or "").strip().upper()

        # 1. Count from CouponUsage relation (joining Coupon and outerjoining Order to exclude cancelled)
        cu_q = (
            select(func.count(CouponUsage.id))
            .join(Coupon, CouponUsage.coupon_id == Coupon.id)
            .outerjoin(Order, CouponUsage.order_id == Order.id)
            .where(
                or_(CouponUsage.coupon_id == coupon.id, func.upper(func.trim(Coupon.code)) == code_upper),
                or_(Order.id.is_(None), Order.status.notin_(["Cancelled", "CANCELLED"]))
            )
        )
        cu_cnt = (await self.db.execute(cu_q)).scalar() or 0

        # 2. Count from Order table directly for matching coupon_code (excluding cancelled)
        ord_q = (
            select(func.count(Order.id))
            .where(
                func.upper(func.trim(Order.coupon_code)) == code_upper,
                Order.status.notin_(["Cancelled", "CANCELLED"])
            )
        )
        ord_cnt = (await self.db.execute(ord_q)).scalar() or 0

        return max(cu_cnt, ord_cnt)

    async def get_user_coupons(self, user_id: str) -> list[UserCouponResponse]:
        """
        Get all coupons for the customer's 'My Coupons' page in the dashboard.
        Preserves all historical/used/expired statuses so the customer can view their coupon history.
        """
        return await self._fetch_coupons(user_id=user_id, only_available=False)

    async def get_available_coupons(self, user_id: str | None = None) -> list[UserCouponResponse]:
        """
        Get only currently eligible and usable coupons for Cart / Checkout.
        Excludes any coupons that are Used (already redeemed by this user), Expired,
        Not Available (not started yet), Inactive, or exceed usage limits.
        """
        return await self._fetch_coupons(user_id=user_id, only_available=True)

    async def _fetch_coupons(self, user_id: str | None = None, only_available: bool = False) -> list[UserCouponResponse]:
        coupons = await self.coupon_repo.get_all()
        now_utc = datetime.now(timezone.utc)

        result = []
        for c in coupons:
            # 1. Coupon Type check: ONLY Customer Coupons are visible in customer available-coupons list
            # Influencer Coupons MUST NOT appear in the customer available coupons list/API
            coupon_type = str(getattr(c, "coupon_type", "CUSTOMER") or "CUSTOMER").strip().upper()
            if coupon_type not in ["CUSTOMER", "CUSTOMER_COUPON", "CUSTOMER COUPON"]:
                continue

            # 2. Check user-specific usage limit (Per-user usage tracking, excluding cancelled orders)
            user_usage = await self._get_coupon_user_usage(c, user_id)

            # 3. Check total usage limit (excluding cancelled orders)
            total_usage = await self._get_coupon_total_usage(c)

            # 4. Dates & Active checks
            is_active_flag = bool(getattr(c, "is_active", True))
            start_dt = (c.start_at if c.start_at.tzinfo else c.start_at.replace(tzinfo=timezone.utc)) if c.start_at else None
            exp_dt = (c.expires_at if c.expires_at.tzinfo else c.expires_at.replace(tzinfo=timezone.utc)) if c.expires_at else None

            is_started = (start_dt <= now_utc) if start_dt else True
            is_not_expired = (exp_dt > now_utc) if exp_dt else True
            is_total_available = (total_usage < c.usage_limit) if c.usage_limit > 0 else True
            is_user_available = (user_usage < c.per_user_usage_limit) if (c.per_user_usage_limit > 0 and user_id and user_id != "guest") else True

            # 5. Check eligibility rules (FIRST_ORDER, SPECIFIC_USERS)
            is_eligible_rule = True
            if hasattr(c, "rules") and c.rules:
                for rule in c.rules:
                    if rule.rule_type == "FIRST_ORDER" and user_id and user_id != "guest":
                        user_orders_q = select(func.count(Order.id)).where(Order.user_id == user_id, Order.status.notin_(["Cancelled", "CANCELLED"]))
                        order_cnt = (await self.db.execute(user_orders_q)).scalar() or 0
                        if order_cnt > 0:
                            is_eligible_rule = False
                    elif rule.rule_type == "SPECIFIC_USERS" and rule.rule_value:
                        allowed_users = [u.strip() for u in rule.rule_value.split(",") if u.strip()]
                        if not user_id or str(user_id) not in allowed_users:
                            is_eligible_rule = False

            # Determine dynamic status: Available / Used / Expired / Not Available / Inactive
            if not is_active_flag:
                status_str = "Inactive"
                is_active = False
            elif not is_total_available or not is_not_expired or not is_eligible_rule:
                status_str = "Expired"
                is_active = False
            elif not is_user_available:
                status_str = "Used"
                is_active = False
            elif not is_started:
                status_str = "Not Available"
                is_active = False
            else:
                status_str = "Available"
                is_active = True

            # If only_available is requested (for Cart / Checkout), exclude used/expired/inactive/not available
            if only_available:
                if status_str != "Available" or not is_active:
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

    async def get_used_coupons(self, user_id: str) -> list[dict]:
        """
        Get all coupon usages for the authenticated customer to display under Used Coupons in Customer Dashboard.
        Strictly returns usages belonging to user_id.
        """
        if not user_id or user_id == "guest":
            return []

        # 1. Fetch from CouponUsage relation
        q = (
            select(CouponUsage, Coupon, Order)
            .join(Coupon, CouponUsage.coupon_id == Coupon.id)
            .outerjoin(Order, CouponUsage.order_id == Order.id)
            .where(CouponUsage.user_id == user_id)
            .order_by(CouponUsage.used_at.desc())
        )
        res = await self.db.execute(q)
        rows = res.all()

        seen_order_coupon = set()
        result = []
        for usage, coupon, order in rows:
            seen_order_coupon.add((usage.order_id, coupon.code.upper()))
            used_date_str = usage.used_at.strftime("%d-%m-%Y") if usage.used_at else ""
            discount_str = ""
            if coupon.discount_type == "PERCENTAGE":
                discount_str = f"{coupon.discount_percent}% OFF"
            elif coupon.discount_type == "FIXED_AMOUNT":
                discount_str = f"₹{coupon.discount_amount} OFF"
            elif coupon.discount_type == "FREE_SHIPPING":
                discount_str = "FREE SHIPPING"
            else:
                discount_str = f"₹{usage.discount_amount:.2f} OFF"

            order_ident = order.id if order else usage.order_id

            result.append({
                "id": usage.id,
                "code": coupon.code,
                "name": coupon.name or coupon.code,
                "description": coupon.description or "",
                "discount_type": coupon.discount_type,
                "discount_percent": coupon.discount_percent,
                "discount_amount": coupon.discount_amount,
                "discount_received": usage.discount_amount,
                "discount_str": discount_str,
                "order_id": order_ident,
                "used_at": used_date_str,
                "used_at_iso": usage.used_at.isoformat() if usage.used_at else None,
                "status": "Used",
            })

        # 2. Also check Order table for any orders placed with coupon_code for this user
        orders_q = (
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.coupon_code.isnot(None),
                Order.status.notin_(["Cancelled", "CANCELLED"])
            )
            .order_by(Order.created_at.desc())
        )
        orders_res = (await self.db.execute(orders_q)).scalars().all()

        for ord_item in orders_res:
            c_code = (ord_item.coupon_code or "").strip().upper()
            if not c_code or (ord_item.id, c_code) in seen_order_coupon:
                continue
            seen_order_coupon.add((ord_item.id, c_code))

            c_obj = await self.coupon_repo.get_by_code(c_code)
            used_date_str = ord_item.created_at.strftime("%d-%m-%Y") if ord_item.created_at else ""
            disc_amt = float(ord_item.coupon_discount or 0.0)

            discount_str = f"₹{disc_amt:.2f} OFF"
            if c_obj:
                if c_obj.discount_type == "PERCENTAGE":
                    discount_str = f"{c_obj.discount_percent}% OFF"
                elif c_obj.discount_type == "FIXED_AMOUNT":
                    discount_str = f"₹{c_obj.discount_amount} OFF"
                elif c_obj.discount_type == "FREE_SHIPPING":
                    discount_str = "FREE SHIPPING"

            result.append({
                "id": f"ord-{ord_item.id}",
                "code": c_code,
                "name": c_obj.name if c_obj else c_code,
                "description": c_obj.description if c_obj else "Coupon applied on order.",
                "discount_type": c_obj.discount_type if c_obj else "PERCENTAGE",
                "discount_percent": c_obj.discount_percent if c_obj else 0.0,
                "discount_amount": c_obj.discount_amount if c_obj else disc_amt,
                "discount_received": disc_amt,
                "discount_str": discount_str,
                "order_id": ord_item.id,
                "used_at": used_date_str,
                "used_at_iso": ord_item.created_at.isoformat() if ord_item.created_at else None,
                "status": "Used",
            })

        return result

    async def validate_and_calculate_discount(
        self,
        user_id: str,
        code: str,
        items: list[dict] | None = None,
        subtotal: float | None = None,
    ) -> CouponValidationResponse:
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
            total_usage = await self._get_coupon_total_usage(coupon)
            if total_usage >= coupon.usage_limit:
                return CouponValidationResponse(valid=False, code=code, message="Promo code usage limit reached.")
                
        # Check per-user usage limit
        if coupon.per_user_usage_limit > 0 and user_id and user_id != "guest":
            user_usage = await self._get_coupon_user_usage(coupon, user_id)
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
        item_count = 0
        
        if items is not None:
            item_count = len(items)
            from app.models.product import Product
            for itm in items:
                pid = itm.get("product_id") or itm.get("id")
                qty = itm.get("quantity", 1)
                price = itm.get("price", 0.0)
                item_price = price * qty
                total_subtotal += item_price

                is_eligible = True
                prod_obj = None
                if pid:
                    prod_obj = await self.db.get(Product, str(pid))

                if allowed_product_ids:
                    prod_matched = (
                        str(pid) in allowed_product_ids
                        or (prod_obj and str(prod_obj.id) in allowed_product_ids)
                        or (prod_obj and prod_obj.sku and str(prod_obj.sku).strip() in allowed_product_ids)
                        or (prod_obj and prod_obj.slug and str(prod_obj.slug).strip() in allowed_product_ids)
                        or (prod_obj and prod_obj.name and str(prod_obj.name).strip().lower() in [p.lower() for p in allowed_product_ids])
                    )
                    if not prod_matched:
                        is_eligible = False

                if allowed_category_ids:
                    cat_matched = False
                    if prod_obj:
                        if prod_obj.category_id and str(prod_obj.category_id) in allowed_category_ids:
                            cat_matched = True
                        elif prod_obj.category and str(prod_obj.category).lower() in [c.lower() for c in allowed_category_ids]:
                            cat_matched = True
                    if not cat_matched:
                        is_eligible = False

                if is_eligible:
                    eligible_subtotal += item_price
        else:
            cart = await self.cart_repo.get_or_create_user_cart(user_id)
            cart_items = cart.items if (cart and cart.items) else []
            item_count = len(cart_items)
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

            if len(cart_items) == 0 and subtotal is not None and subtotal > 0 and not allowed_product_ids and not allowed_category_ids:
                eligible_subtotal = subtotal
                total_subtotal = subtotal

        if item_count > 0 and (allowed_category_ids or allowed_product_ids) and eligible_subtotal == 0.0:
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
