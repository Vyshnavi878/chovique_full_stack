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

    if not x_razorpay_signature:
        logger.warning("Missing Razorpay webhook signature header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header.",
        )

    is_valid = razorpay_client.verify_webhook_signature(body_bytes, x_razorpay_signature)
    if not is_valid:
        logger.warning("Invalid Razorpay webhook signature received.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay webhook signature.",
        )

    try:
        payload = await request.json()
        event = payload.get("event")
        logger.info("Received verified Razorpay webhook event: %s", event)

        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")

        if event == "payment.captured":
            if razorpay_order_id and razorpay_payment_id:
                from app.services.payment_service import PaymentService
                payment_service = PaymentService(db)
                await payment_service.finalize_online_payment(
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                )

        elif event == "payment.failed":
            if razorpay_order_id:
                payment_repo = PaymentRepository(db)
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
