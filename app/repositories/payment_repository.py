from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payment import Payment


class PaymentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payment(
        self,
        order_id: str,
        user_id: str,
        razorpay_order_id: str,
        amount: float,
        currency: str = "INR",
    ) -> Payment:
        payment = Payment(
            order_id=order_id,
            user_id=user_id,
            razorpay_order_id=razorpay_order_id,
            amount=amount,
            currency=currency,
            status="created",
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_by_razorpay_order_id(self, razorpay_order_id: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.razorpay_order_id == razorpay_order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_razorpay_payment_id(self, razorpay_payment_id: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.razorpay_payment_id == razorpay_payment_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        razorpay_order_id: str,
        status: str,
        razorpay_payment_id: str | None = None,
        razorpay_signature: str | None = None,
        error_message: str | None = None,
    ) -> Payment | None:
        values = {"status": status}
        if razorpay_payment_id:
            values["razorpay_payment_id"] = razorpay_payment_id
        if razorpay_signature:
            values["razorpay_signature"] = razorpay_signature
        if error_message:
            values["error_message"] = error_message

        await self.db.execute(
            update(Payment)
            .where(Payment.razorpay_order_id == razorpay_order_id)
            .values(**values)
        )
        await self.db.commit()
        return await self.get_by_razorpay_order_id(razorpay_order_id)
