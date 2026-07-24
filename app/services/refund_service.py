import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.razorpay import razorpay_client
from app.integrations.resend import resend_email
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.refund_repository import RefundRepository
from app.repositories.user_repository import UserRepository
from app.schemas.refund import InitiateRefundPayload, RefundResponseSchema

logger = logging.getLogger(__name__)


class RefundService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.refund_repo = RefundRepository(db)
        self.order_repo = OrderRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)
        self.user_repo = UserRepository(db)

    async def initiate_refund(
        self,
        payload: InitiateRefundPayload,
        performed_by_admin_id: Optional[str] = None,
    ) -> RefundResponseSchema:
        """
        Execute partial or full refund for an order via Razorpay & record audit.
        """
        order = await self.order_repo.get_by_id(payload.order_id)
        if not order:
            raise ValueError("Order not found.")

        # Find payment transaction for order
        payments = getattr(order, "payments", [])
        payment = next((p for p in payments if p.status == "captured"), None)

        refund_amount = payload.amount if payload.amount is not None else order.total
        if refund_amount <= 0 or refund_amount > order.total:
            raise ValueError(f"Invalid refund amount: {refund_amount}. Must be between 0 and {order.total}.")

        razorpay_refund_id = None

        if payment and payment.razorpay_payment_id:
            try:
                rzp_res = razorpay_client.refund_payment(
                    razorpay_payment_id=payment.razorpay_payment_id,
                    amount=refund_amount,
                    notes={"order_id": order.id, "reason": payload.reason or ""},
                )
                razorpay_refund_id = rzp_res.get("id")
            except Exception as e:
                logger.error("Razorpay refund execution failed: %s", e)

        refund = await self.refund_repo.create_refund(
            order_id=order.id,
            amount=refund_amount,
            payment_id=payment.id if payment else None,
            razorpay_refund_id=razorpay_refund_id,
            reason=payload.reason,
            status="processed",
        )

        # Send refund notification email
        user = await self.user_repo.get_by_id(order.user_id)
        if user:
            await resend_email.send_refund_notification(
                email=user.email,
                name=user.full_name,
                order_id=order.id,
                amount=refund_amount,
            )

        return RefundResponseSchema.model_validate(refund)

    async def get_order_refunds(self, order_id: str) -> list[RefundResponseSchema]:
        refunds = await self.refund_repo.get_by_order_id(order_id)
        return [RefundResponseSchema.model_validate(r) for r in refunds]
