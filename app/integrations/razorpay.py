import hmac
import hashlib
import logging
import time
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Base URL for Razorpay REST API (QR Codes endpoint not in Python SDK)
RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class RazorpayIntegration:
    """
    Razorpay integration wrapper for order creation, QR code generation,
    signature verification, webhook verification, and refund processing.
    """

    @property
    def key_id(self) -> str:
        return settings.RAZORPAY_KEY_ID

    @property
    def key_secret(self) -> str:
        return settings.RAZORPAY_KEY_SECRET

    @property
    def webhook_secret(self) -> str:
        return settings.RAZORPAY_WEBHOOK_SECRET

    def create_qr_code(
        self,
        amount: float,
        razorpay_order_id: str,
        description: Optional[str] = None,
        close_by_seconds: int = 600,  # Default: 10 minutes
    ) -> Dict[str, Any]:
        """
        Create a dynamic, fixed-amount, single-use Razorpay QR Code for UPI payments.

        Uses the Razorpay REST API directly (POST /v1/payments/qr_codes) since the
        Python SDK does not expose this endpoint.

        Args:
            amount: Amount in major units (INR). Converted to paise internally.
            razorpay_order_id: The Razorpay Order ID to associate with this QR code.
            description: Optional description shown in the UPI app.
            close_by_seconds: Number of seconds from now before the QR code expires.
                              Razorpay allows 5–15 minutes (300–900 seconds).

        Returns:
            Razorpay QR Code entity dict containing: id, image_url, close_by, etc.
        """
        try:
            import httpx
        except ImportError:
            logger.error("httpx package is not installed. Required for QR Code API.")
            raise RuntimeError("httpx is required for QR Code payments. Run: pip install httpx")

        amount_in_paise = int(round(amount * 100))
        close_by_ts = int(time.time()) + close_by_seconds

        payload = {
            "type": "upi_qr",
            "name": description or "Chovique Payment",
            "usage": "single_use",
            "fixed_amount": True,
            "payment_amount": amount_in_paise,
            "description": description or f"Payment for Order {razorpay_order_id}",
            "close_by": close_by_ts,
            "notes": {
                "razorpay_order_id": razorpay_order_id,
            },
        }

        try:
            response = httpx.post(
                f"{RAZORPAY_API_BASE}/payments/qr_codes",
                auth=(self.key_id, self.key_secret),
                json=payload,
                timeout=15.0,
            )
            response.raise_for_status()
            qr_data = response.json()
            logger.info(
                "Created Razorpay QR Code %s for order %s, amount ₹%.2f, expires at %s",
                qr_data.get("id"), razorpay_order_id, amount, close_by_ts,
            )
            return qr_data
        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error("Razorpay QR Code API error: %s — %s", e.response.status_code, error_body)
            raise ValueError(f"Razorpay QR Code creation failed: {error_body}")
        except Exception as e:
            logger.error("Razorpay QR Code creation error: %s", e)
            raise ValueError(f"Razorpay QR Code creation failed: {e}")

    def close_qr_code(self, qr_code_id: str) -> Dict[str, Any]:
        """
        Close (expire) an active Razorpay QR Code early.
        Useful for cleanup when the user cancels or retries.
        """
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required for QR Code payments.")

        try:
            response = httpx.post(
                f"{RAZORPAY_API_BASE}/payments/qr_codes/{qr_code_id}/close",
                auth=(self.key_id, self.key_secret),
                timeout=10.0,
            )
            response.raise_for_status()
            logger.info("Closed Razorpay QR Code %s", qr_code_id)
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning("Could not close QR Code %s: %s", qr_code_id, e.response.text)
            return {}
        except Exception as e:
            logger.warning("Could not close QR Code %s: %s", qr_code_id, e)
            return {}

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
