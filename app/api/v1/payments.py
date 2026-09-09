import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.integrations.razorpay import razorpay_client
from app.models.user import User
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import VerifyPaymentPayload
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────

class QRCodeRequest(BaseModel):
    razorpay_order_id: str
    amount: float  # In major units (INR), e.g. 1299.00
    order_id: str  # Internal Chovique order ID for description


# ─────────────────────────────────────────────────────────────────────────────
# Existing: Verify Razorpay payment signature
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/verify", summary="Verify Razorpay payment signature & confirm order")
async def verify_payment(
    payload: VerifyPaymentPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = PaymentService(db)
        return await service.verify_payment(current_user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Generate Razorpay UPI QR Code for a Razorpay Order
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/qr-code", summary="Generate a dynamic UPI QR Code for an existing Razorpay order")
async def generate_qr_code(
    payload: QRCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a Razorpay dynamic, fixed-amount, single-use UPI QR Code tied to
    the given Razorpay Order. Stores the qr_code_id on the Payment record for
    webhook and polling lookups.

    Returns:
        qr_code_id: Razorpay QR Code identifier (e.g. qr_AbcDef123)
        image_url: PNG image URL of the QR code to render in the frontend
        close_by: Unix timestamp when the QR code expires (10 minutes from now)
    """
    payment_repo = PaymentRepository(db)

    # Validate that this payment belongs to the authenticated user
    payment = await payment_repo.get_by_razorpay_order_id(payload.razorpay_order_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found for given Razorpay order ID.",
        )
    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this payment.",
        )
    if payment.status == "captured":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order has already been paid.",
        )

    try:
        qr_data = razorpay_client.create_qr_code(
            amount=payload.amount,
            razorpay_order_id=payload.razorpay_order_id,
            description=f"Chovique Order #{payload.order_id[:8].upper()}",
        )
    except (ValueError, RuntimeError) as e:
        logger.error("QR code generation failed for order %s: %s", payload.order_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"QR Code generation failed: {e}",
        )

    qr_code_id = qr_data.get("id")
    image_url = qr_data.get("image_url")
    close_by = qr_data.get("close_by")

    if not qr_code_id or not image_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Razorpay returned an incomplete QR Code response.",
        )

    # Persist the QR Code ID on the payment record so the webhook can find it
    await payment_repo.set_qr_code_id(
        razorpay_order_id=payload.razorpay_order_id,
        qr_code_id=qr_code_id,
    )

    logger.info(
        "QR Code %s generated for user %s, order %s",
        qr_code_id, current_user.id, payload.order_id,
    )

    return {
        "qr_code_id": qr_code_id,
        "image_url": image_url,
        "close_by": close_by,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Poll QR payment status (called by frontend every 3 seconds)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/qr-status/{qr_code_id}", summary="Poll UPI QR Code payment status")
async def get_qr_payment_status(
    qr_code_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the current payment status for a QR Code payment.
    The frontend polls this every 3 seconds while showing the QR code.

    When status becomes 'captured', the frontend transitions to the success screen.

    Returns:
        status: 'created' | 'captured' | 'failed'
        order_id: Internal Chovique order ID (needed for success screen fetch)
    """
    payment_repo = PaymentRepository(db)
    payment = await payment_repo.get_by_qr_code_id(qr_code_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR Code payment record not found.",
        )

    # Ownership check — prevent IDOR
    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this payment.",
        )

    return {
        "status": payment.status,
        "order_id": payment.order_id,
    }
