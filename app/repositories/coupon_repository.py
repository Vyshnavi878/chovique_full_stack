import datetime
from datetime import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.coupon import Coupon


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
        coupon = Coupon(**kwargs)
        self._check_and_deactivate(coupon)
        self.db.add(coupon)
        await self.db.commit()
        await self.db.refresh(coupon)
        return coupon

    async def update(self, code: str, **kwargs) -> Coupon | None:
        coupon = await self.get_by_code(code)
        if not coupon:
            return None
        
        if "expires_at" in kwargs:
            kwargs["expires_at"] = self._parse_expires_at(kwargs["expires_at"])
            
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
