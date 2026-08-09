import datetime
from datetime import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.coupon import Coupon, CouponEligibilityRule, CouponProduct, CouponCategory


class CouponRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    def _parse_expires_at(self, val):
        if not val:
            return None
        if isinstance(val, datetime.datetime):
            return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
        if isinstance(val, str):
            try:
                val_str = val.strip()
                if len(val_str) == 10:
                    val_str += "T23:59:59+00:00"
                dt = datetime.datetime.fromisoformat(val_str)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                return None
        return None

    def _check_and_deactivate(self, coupon: Coupon) -> bool:
        if coupon and coupon.expires_at:
            now_utc = datetime.datetime.now(timezone.utc)
            exp = coupon.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now_utc >= exp and coupon.is_active:
                coupon.is_active = False
                return True
        return False

    async def get_by_code(self, code: str) -> Coupon | None:
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == code.upper())
        )
        coupon = result.scalar_one_or_none()
        if coupon and self._check_and_deactivate(coupon):
            await self.db.commit()
            await self.db.refresh(coupon)
        return coupon

    async def get_active_coupons(self) -> list[Coupon]:
        coupons = await self.get_all()
        return [c for c in coupons if c.is_active]

    async def get_all(self) -> list[Coupon]:
        result = await self.db.execute(select(Coupon).order_by(Coupon.created_at.desc()))
        coupons = list(result.scalars().all())
        updated = False
        for c in coupons:
            if self._check_and_deactivate(c):
                updated = True
        if updated:
            await self.db.commit()
            for c in coupons:
                await self.db.refresh(c)
        return coupons

    async def create(self, **kwargs) -> Coupon:
        kwargs["code"] = kwargs["code"].upper()
        if "expires_at" in kwargs and kwargs["expires_at"]:
            kwargs["expires_at"] = self._parse_expires_at(kwargs["expires_at"])
        if "start_at" in kwargs and kwargs["start_at"]:
            kwargs["start_at"] = self._parse_expires_at(kwargs["start_at"])

        eligibility_rule = kwargs.pop("eligibility_rule", None)
        eligibility_value = kwargs.pop("eligibility_value", None)
        applicability = kwargs.pop("applicability", None)
        applicable_ids = kwargs.pop("applicable_ids", [])

        # Filter kwargs to only columns present on Coupon ORM model
        valid_kwargs = {k: v for k, v in kwargs.items() if hasattr(Coupon, k)}

        coupon = Coupon(**valid_kwargs)
        self._check_and_deactivate(coupon)
        self.db.add(coupon)
        await self.db.flush()

        if eligibility_rule and eligibility_rule != "ALL_USERS":
            rule = CouponEligibilityRule(
                coupon_id=coupon.id,
                rule_type=eligibility_rule,
                rule_value=str(eligibility_value) if eligibility_value else None,
            )
            self.db.add(rule)

        if applicability in ("SPECIFIC_PRODUCTS", "PRODUCTS") and applicable_ids:
            for pid in applicable_ids:
                if pid:
                    self.db.add(CouponProduct(coupon_id=coupon.id, product_id=str(pid)))
        elif applicability in ("SPECIFIC_CATEGORIES", "CATEGORIES") and applicable_ids:
            for cid in applicable_ids:
                if cid:
                    self.db.add(CouponCategory(coupon_id=coupon.id, category_id=str(cid)))

        await self.db.commit()
        await self.db.refresh(coupon)
        return coupon

    async def update(self, code: str, **kwargs) -> Coupon | None:
        coupon = await self.get_by_code(code)
        if not coupon:
            return None
        
        if "expires_at" in kwargs and kwargs["expires_at"]:
            kwargs["expires_at"] = self._parse_expires_at(kwargs["expires_at"])
        if "start_at" in kwargs and kwargs["start_at"]:
            kwargs["start_at"] = self._parse_expires_at(kwargs["start_at"])

        kwargs.pop("eligibility_rule", None)
        kwargs.pop("eligibility_value", None)
        kwargs.pop("applicability", None)
        kwargs.pop("applicable_ids", None)

        for key, value in kwargs.items():
            if hasattr(coupon, key) and value is not None:
                setattr(coupon, key, value)
                
        self._check_and_deactivate(coupon)
        await self.db.commit()
        await self.db.refresh(coupon)
        return coupon

    async def delete(self, code: str) -> bool:
        coupon = await self.get_by_code(code)
        if not coupon:
            return False
        await self.db.delete(coupon)
        await self.db.commit()
        return True

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(select(func.count()).select_from(Coupon))
        return result.scalar() or 0
