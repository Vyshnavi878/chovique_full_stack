from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.coupon import Coupon


class CouponRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_code(self, code: str) -> Coupon | None:
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == code.upper(), Coupon.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_active_coupons(self) -> list[Coupon]:
        result = await self.db.execute(
            select(Coupon).where(Coupon.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[Coupon]:
        result = await self.db.execute(select(Coupon).order_by(Coupon.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Coupon:
        kwargs["code"] = kwargs["code"].upper()
        coupon = Coupon(**kwargs)
        self.db.add(coupon)
        await self.db.commit()
        await self.db.refresh(coupon)
        return coupon

    async def update(self, code: str, **kwargs) -> Coupon | None:
        coupon = await self.get_by_code(code)
        if not coupon:
            return None
        
        for key, value in kwargs.items():
            if hasattr(coupon, key) and value is not None:
                setattr(coupon, key, value)
                
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
