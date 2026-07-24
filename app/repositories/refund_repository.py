from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.refund import Refund


class RefundRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_refund(
        self,
        order_id: str,
        amount: float,
        payment_id: str | None = None,
        razorpay_refund_id: str | None = None,
        reason: str | None = None,
        status: str = "processed",
    ) -> Refund:
        refund = Refund(
            order_id=order_id,
            payment_id=payment_id,
            razorpay_refund_id=razorpay_refund_id,
            amount=amount,
            reason=reason,
            status=status,
        )
        self.db.add(refund)
        await self.db.commit()
        await self.db.refresh(refund)
        return refund

    async def get_by_order_id(self, order_id: str) -> list[Refund]:
        result = await self.db.execute(
            select(Refund)
            .where(Refund.order_id == order_id)
            .order_by(Refund.created_at.desc())
        )
        return list(result.scalars().all())
