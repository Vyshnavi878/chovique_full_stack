import logging
from typing import Optional, List, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class ResendEmailIntegration:
    """
    Resend API Integration for transactional emails.
    Sends emails using Resend REST API if API key is configured,
    or logs in dev mode.
    """

    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_email = settings.MAIL_FROM or "Chovique Chocolatier <onboarding@resend.dev>"
        self.api_url = "https://api.resend.com/emails"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send a single email via Resend API."""
        if not self.api_key:
            logger.info("[RESEND DEV MODE] Email to %s | Subject: %s", to_email, subject)
            return True

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        if text_content:
            payload["text"] = text_content

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=10.0)
                if response.status_code in (200, 201):
                    logger.info("Resend email sent successfully to %s", to_email)
                    return True
                else:
                    logger.error("Resend API error [%d]: %s", response.status_code, response.text)
                    return False
        except Exception as e:
            logger.error("Failed to send Resend email to %s: %s", to_email, e)
            return False

    # ==========================================================
    # Transactional Email Methods
    # ==========================================================

    async def send_welcome(self, email: str, name: str):
        subject = "Welcome to Chovique Chocolatier ✨"
        html = f"""
        <h2>Welcome to Chovique, {name}!</h2>
        <p>Thank you for creating an account with us. Prepare to indulge in world-class handcrafted chocolates.</p>
        <br/>
        <p>Best regards,<br/>The Chovique Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_order_confirmation(self, email: str, name: str, order_id: str, total: float):
        subject = f"Order Confirmation — #{order_id}"
        html = f"""
        <h2>Order Received!</h2>
        <p>Dear {name},</p>
        <p>Your order <strong>#{order_id}</strong> of <strong>₹{total:.2f}</strong> has been successfully placed and is being prepared.</p>
        """
        return await self.send_email(email, subject, html)

    async def send_shipping_update(self, email: str, name: str, order_id: str, tracking_number: str):
        subject = f"Order #{order_id} Has Been Shipped! 🚚"
        html = f"""
        <h2>Your Order is on the Way!</h2>
        <p>Dear {name},</p>
        <p>Order <strong>#{order_id}</strong> is shipped! Tracking Number: <strong>{tracking_number}</strong></p>
        """
        return await self.send_email(email, subject, html)

    async def send_cancellation(self, email: str, name: str, order_id: str):
        subject = f"Order #{order_id} Cancellation"
        html = f"""
        <h2>Order Cancelled</h2>
        <p>Dear {name},</p>
        <p>Order <strong>#{order_id}</strong> has been cancelled. If any payment was captured, a refund will be processed to your account.</p>
        """
        return await self.send_email(email, subject, html)

    async def send_refund_notification(self, email: str, name: str, order_id: str, amount: float):
        subject = f"Refund Processed for Order #{order_id}"
        html = f"""
        <h2>Refund Processed</h2>
        <p>Dear {name},</p>
        <p>A refund of <strong>₹{amount:.2f}</strong> for Order <strong>#{order_id}</strong> has been issued.</p>
        """
        return await self.send_email(email, subject, html)


resend_email = ResendEmailIntegration()
