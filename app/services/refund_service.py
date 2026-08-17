import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.razorpay import razorpay_client
from app.integrations.resend import resend_email
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
        self.user_repo = UserRepository(db)

    async def initiate_refund(
        self,
        payload: InitiateRefundPayload,
        performed_by_admin_id: Optional[str] = None,
    ) -> RefundResponseSchema:
        """
        Execute partial or full refund for an order via Razorpay & record audit.
        """
        from app.repositories.platform_settings_repository import PlatformSettingsRepository
        ps_repo = PlatformSettingsRepository(self.db)
        ps = await ps_repo.get()
        if not ps.return_refund_enabled:
            raise ValueError("Return and refund functionality is currently disabled by system configuration.")

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

        # Update payment_status independently
        order.payment_status = "Refunded" if refund_amount >= order.total else "Partially Refunded"
        await self.db.commit()

        # Send refund notification email & in-app notification
        user = await self.user_repo.get_by_id(order.user_id)
        if user:
            await resend_email.send_refund_notification(
                email=user.email,
                name=user.full_name,
                order_id=order.id,
                amount=refund_amount,
            )
            try:
                from app.repositories.notification_repository import NotificationRepository
                notif_repo = NotificationRepository(self.db)
                await notif_repo.create(
                    user_id=order.user_id,
                    type="refund",
                    title="Refund Processed",
                    message=f"A refund of ₹{refund_amount:,.2f} for Order #{order.id} has been issued.",
                    text=f"A refund of ₹{refund_amount:,.2f} for Order #{order.id} has been issued.",
                    related_entity_type="order",
                    related_entity_id=order.id,
                    reference_id=order.id,
                )
            except Exception as notif_err:
                logger.warning("Failed to create customer in-app refund notification: %s", notif_err)

        # Notify Admin
        try:
            from app.services.notification_service import NotificationService
            await NotificationService(self.db).notify_refund_completed(order_id=order.id, amount=refund_amount)
        except Exception as admin_notif_err:
            logger.warning("Failed to create admin refund notification: %s", admin_notif_err)

        return RefundResponseSchema.model_validate(refund)

    async def get_order_refunds(self, order_id: str) -> list[RefundResponseSchema]:
        refunds = await self.refund_repo.get_by_order_id(order_id)
        return [RefundResponseSchema.model_validate(r) for r in refunds]
