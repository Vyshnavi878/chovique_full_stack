import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.integrations.razorpay import razorpay_client
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

        # ─────────────────────────────────────────────────────────────────────
        # Standard Payment Events (Razorpay modal — Credit Card, UPI, NetBanking)
        # ─────────────────────────────────────────────────────────────────────

        if event == "payment.captured":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_order_id = payment_entity.get("order_id")
            razorpay_payment_id = payment_entity.get("id")

            if razorpay_order_id and razorpay_payment_id:
                from app.services.payment_service import PaymentService
                payment_service = PaymentService(db)
                await payment_service.finalize_online_payment(
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                )

        elif event == "payment.failed":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_order_id = payment_entity.get("order_id")
            razorpay_payment_id = payment_entity.get("id")

            if razorpay_order_id:
                payment_repo = PaymentRepository(db)
                await payment_repo.update_status(
                    razorpay_order_id=razorpay_order_id,
                    status="failed",
                    razorpay_payment_id=razorpay_payment_id,
                    error_message=payment_entity.get("error_description"),
                )

        # ─────────────────────────────────────────────────────────────────────
        # UPI QR Code Payment Event
        #
        # Razorpay fires `qr_code.credited` when a customer scans and pays.
        # Payload structure:
        #   payload.payment.entity  → razorpay payment details (id, amount, etc.)
        #   payload.qr_code.entity  → qr code details (id, notes → razorpay_order_id)
        #
        # We use the qr_code_id to look up the Payment record (by qr_code_id column)
        # and then call the same finalize_online_payment() used by the modal flow.
        # This ensures: inventory deduction, wallet, coupon, cart clear, email, invoice.
        # ─────────────────────────────────────────────────────────────────────

        elif event == "qr_code.credited":
            qr_entity = payload.get("payload", {}).get("qr_code", {}).get("entity", {})
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

            qr_code_id = qr_entity.get("id")
            razorpay_payment_id = payment_entity.get("id")

            # The razorpay_order_id is stored in the QR code's notes (we set it at creation)
            # and is also derivable by looking up the DB record by qr_code_id.
            if qr_code_id:
                payment_repo = PaymentRepository(db)
                payment = await payment_repo.get_by_qr_code_id(qr_code_id)

                if payment:
                    logger.info(
                        "QR Code credited: qr_code_id=%s, payment_id=%s, order_id=%s",
                        qr_code_id, razorpay_payment_id, payment.order_id,
                    )
                    from app.services.payment_service import PaymentService
                    payment_service = PaymentService(db)
                    await payment_service.finalize_online_payment(
                        razorpay_order_id=payment.razorpay_order_id,
                        razorpay_payment_id=razorpay_payment_id or "",
                    )
                else:
                    logger.warning(
                        "qr_code.credited: No payment record found for qr_code_id=%s", qr_code_id
                    )
            else:
                logger.warning("qr_code.credited event received without a qr_code entity ID.")

        else:
            logger.debug("Unhandled Razorpay event: %s", event)

        return {"status": "ok", "event": event}

    except Exception as e:
        logger.error("Error processing Razorpay webhook: %s", e)
        return {"status": "error", "detail": str(e)}
