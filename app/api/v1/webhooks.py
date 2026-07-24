import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.integrations.razorpay import razorpay_client
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/razorpay", summary="Razorpay Webhook Handler")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db),
):
    body_bytes = await request.body()

    if x_razorpay_signature:
        is_valid = razorpay_client.verify_webhook_signature(body_bytes, x_razorpay_signature)
        if not is_valid:
            logger.warning("Invalid Razorpay webhook signature received.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature.")

    try:
        payload = await request.json()
        event = payload.get("event")
        logger.info("Received Razorpay webhook event: %s", event)

        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")

        payment_repo = PaymentRepository(db)
        order_repo = OrderRepository(db)

        if event == "payment.captured":
            if razorpay_order_id:
                payment = await payment_repo.get_by_razorpay_order_id(razorpay_order_id)
                if payment and payment.status != "captured":
                    await payment_repo.update_status(
                        razorpay_order_id=razorpay_order_id,
                        status="captured",
                        razorpay_payment_id=razorpay_payment_id,
                    )
                    order = await order_repo.get_by_id(payment.order_id)
                    if order:
                        order.status = "Processing"
                        await db.commit()

        elif event == "payment.failed":
            if razorpay_order_id:
                await payment_repo.update_status(
                    razorpay_order_id=razorpay_order_id,
                    status="failed",
                    razorpay_payment_id=razorpay_payment_id,
                    error_message=payment_entity.get("error_description"),
                )

        return {"status": "ok", "event": event}

    except Exception as e:
        logger.error("Error processing Razorpay webhook: %s", e)
        return {"status": "error", "detail": str(e)}
