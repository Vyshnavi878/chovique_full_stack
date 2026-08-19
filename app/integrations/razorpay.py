import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class RazorpayIntegration:
    """
    Razorpay integration wrapper for order creation, signature verification,
    webhook verification, and refund processing.
    """

    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    def create_order(
        self,
        amount: float,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create Razorpay Order.
        Amount must be provided in major currency units (e.g. INR),
        converted internally to paise (amount * 100).
        """
        amount_in_paise = int(round(amount * 100))

        try:
            import razorpay
            client = razorpay.Client(auth=(self.key_id, self.key_secret))
            data = {
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": receipt or "",
                "notes": notes or {},
            }
            order = client.order.create(data=data)
            logger.info("Created Razorpay order %s for amount %s", order.get("id"), amount)
            return order
        except ImportError:
            logger.error("razorpay Python package is not installed.")
            raise RuntimeError("Razorpay SDK is not installed in runtime environment.")
        except Exception as e:
            logger.error("Error creating Razorpay order: %s", e)
            raise ValueError(f"Razorpay order creation failed: {e}")

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Verify Razorpay payment signature using HMAC SHA256.
        Prevents tampering with payment status.
        """
        if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
            return False

        if not self.key_secret:
            logger.error("RAZORPAY_KEY_SECRET is not configured.")
            return False

        try:
            import razorpay
            client = razorpay.Client(auth=(self.key_id, self.key_secret))
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
            return True
        except ImportError:
            msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
            generated_sig = hmac.new(
                self.key_secret.encode("utf-8"),
                msg,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(generated_sig, razorpay_signature)
        except Exception as e:
            logger.warning("Razorpay signature verification failed: %s", e)
            return False

    def verify_webhook_signature(
        self,
        body_bytes: bytes,
        signature: str,
        secret: Optional[str] = None,
    ) -> bool:
        """
        Verify Razorpay webhook signature using HMAC SHA256.
        """
        secret_key = secret or self.webhook_secret
        if not secret_key or not signature:
            return False

        try:
            expected_sig = hmac.new(
                secret_key.encode("utf-8"),
                body_bytes,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected_sig, signature)
        except Exception as e:
            logger.error("Razorpay webhook signature verification error: %s", e)
            return False

    def refund_payment(
        self,
        razorpay_payment_id: str,
        amount: Optional[float] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Refund payment partially or fully.
        """
        try:
            import razorpay
            client = razorpay.Client(auth=(self.key_id, self.key_secret))
            data = {}
            if amount is not None:
                data["amount"] = int(round(amount * 100))
            if notes:
                data["notes"] = notes

            refund = client.payment.refund(razorpay_payment_id, data)
            logger.info("Razorpay refund %s processed for payment %s", refund.get("id"), razorpay_payment_id)
            return refund
        except ImportError:
            logger.error("razorpay Python package is not installed.")
            raise RuntimeError("Razorpay SDK is not installed in runtime environment.")
        except Exception as e:
            logger.error("Razorpay refund failed: %s", e)
            raise ValueError(f"Razorpay refund failed: {e}")


razorpay_client = RazorpayIntegration()
