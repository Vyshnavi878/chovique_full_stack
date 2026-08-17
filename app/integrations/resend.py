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
        self.platform_name = getattr(settings, "PROJECT_NAME", "Chovique Chocolatier")
        self.api_url = "https://api.resend.com/emails"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send a single email via existing SMTP infrastructure."""
        try:
            from app.services.mail_service import MailService
            return await MailService.send_generic_email(
                email=to_email,
                subject=subject,
                html_content=html_content,
            )
        except Exception as e:
            logger.error("Failed to send SMTP email to %s: %s", to_email, e)
            return False

    # ==========================================================
    # 1. SUPER ADMIN EMAIL NOTIFICATIONS
    # ==========================================================

    async def send_superadmin_new_admin(self, super_admin_email: str, super_admin_name: str, admin_name: str, admin_email: str, created_at: str):
        subject = "New Admin Account Created"
        html = f"""
        <p>Hello {super_admin_name},</p>
        <p>A new admin account has been created on {self.platform_name}.</p>
        <p><strong>Admin Details:</strong></p>
        <ul>
            <li><strong>Name:</strong> {admin_name}</li>
            <li><strong>Email:</strong> {admin_email}</li>
            <li><strong>Created On:</strong> {created_at}</li>
        </ul>
        <p>Please review the admin account from the Admin Management section.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(super_admin_email, subject, html)

    async def send_superadmin_admin_activated(self, super_admin_email: str, super_admin_name: str, admin_name: str, admin_email: str, activated_at: str):
        subject = "Admin Account Activated"
        html = f"""
        <p>Hello {super_admin_name},</p>
        <p>The admin account for <strong>{admin_name}</strong> ({admin_email}) has been activated successfully.</p>
        <p><strong>Activated On:</strong> {activated_at}</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(super_admin_email, subject, html)

    async def send_superadmin_admin_deactivated(self, super_admin_email: str, super_admin_name: str, admin_name: str, admin_email: str, deactivated_at: str):
        subject = "Admin Account Deactivated"
        html = f"""
        <p>Hello {super_admin_name},</p>
        <p>The admin account for <strong>{admin_name}</strong> ({admin_email}) has been deactivated.</p>
        <p><strong>Deactivated On:</strong> {deactivated_at}</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(super_admin_email, subject, html)

    async def send_superadmin_admin_updated(self, super_admin_email: str, super_admin_name: str, admin_name: str, admin_email: str, updated_at: str):
        subject = "Admin Profile Updated"
        html = f"""
        <p>Hello {super_admin_name},</p>
        <p>The profile of admin <strong>{admin_name}</strong> has been updated.</p>
        <p><strong>Admin Email:</strong> {admin_email}<br/><strong>Updated On:</strong> {updated_at}</p>
        <p>Please review the changes from Admin Management if required.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(super_admin_email, subject, html)

    async def send_superadmin_admin_password_updated(self, super_admin_email: str, super_admin_name: str, admin_name: str, admin_email: str, updated_at: str):
        subject = "Admin Password Updated"
        html = f"""
        <p>Hello {super_admin_name},</p>
        <p>The password for admin account <strong>{admin_email}</strong> was updated.</p>
        <p><strong>Admin:</strong> {admin_name}<br/><strong>Updated On:</strong> {updated_at}</p>
        <p>If this activity was unexpected, please review the admin account immediately.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Security Team</p>
        """
        return await self.send_email(super_admin_email, subject, html)

    async def send_superadmin_security_alert(self, super_admin_email: str, super_admin_name: str, admin_email: str, security_event: str, detected_at: str):
        subject = "Admin Security Alert"
        html = f"""
        <p>Hello {super_admin_name},</p>
        <p>A security event was detected for admin account <strong>{admin_email}</strong>.</p>
        <p><strong>Event:</strong> {security_event}<br/><strong>Detected On:</strong> {detected_at}</p>
        <p>Please review the account and take appropriate action if required.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Security Team</p>
        """
        return await self.send_email(super_admin_email, subject, html)

    async def send_superadmin_platform_alert(self, super_admin_email: str, super_admin_name: str, alert_title: str, alert_message: str, occurred_at: str):
        subject = "Critical Platform Alert"
        html = f"""
        <p>Hello {super_admin_name},</p>
        <p>A critical platform event requires your attention.</p>
        <p><strong>Alert:</strong> {alert_title}<br/><strong>Details:</strong> {alert_message}<br/><strong>Occurred On:</strong> {occurred_at}</p>
        <p>Please review the platform immediately.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(super_admin_email, subject, html)

    # ==========================================================
    # 2. ADMIN EMAIL NOTIFICATIONS
    # ==========================================================

    async def send_admin_new_order(self, admin_email: str, admin_name: str, order_id: str, customer_name: str, order_total: float, payment_status: str, order_date: str):
        subject = f"New Order Received – #{order_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>A new order has been placed.</p>
        <ul>
            <li><strong>Order ID:</strong> #{order_id}</li>
            <li><strong>Customer:</strong> {customer_name}</li>
            <li><strong>Order Amount:</strong> ₹{order_total:,.2f}</li>
            <li><strong>Payment Status:</strong> {payment_status}</li>
            <li><strong>Order Date:</strong> {order_date}</li>
        </ul>
        <p>Please review the order from the Admin Dashboard.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_payment_success(self, admin_email: str, admin_name: str, order_id: str, customer_name: str, amount: float, payment_method: str, payment_date: str):
        subject = f"Payment Successful – Order #{order_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>Payment for order <strong>#{order_id}</strong> was completed successfully.</p>
        <ul>
            <li><strong>Customer:</strong> {customer_name}</li>
            <li><strong>Amount:</strong> ₹{amount:,.2f}</li>
            <li><strong>Payment Method:</strong> {payment_method}</li>
            <li><strong>Payment Date:</strong> {payment_date}</li>
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_payment_failure(self, admin_email: str, admin_name: str, order_id: str, customer_name: str, amount: float, payment_method: str, failure_reason: str):
        subject = f"Payment Failed – Order #{order_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>Payment for order <strong>#{order_id}</strong> has failed.</p>
        <ul>
            <li><strong>Customer:</strong> {customer_name}</li>
            <li><strong>Amount:</strong> ₹{amount:,.2f}</li>
            <li><strong>Payment Method:</strong> {payment_method}</li>
            <li><strong>Failure Reason:</strong> {failure_reason}</li>
        </ul>
        <p>Please review the order/payment status.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_order_cancelled(self, admin_email: str, admin_name: str, order_id: str, customer_name: str, order_total: float, cancelled_at: str, cancellation_reason: str):
        subject = f"Order Cancelled – #{order_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>Order <strong>#{order_id}</strong> has been cancelled.</p>
        <ul>
            <li><strong>Customer:</strong> {customer_name}</li>
            <li><strong>Order Amount:</strong> ₹{order_total:,.2f}</li>
            <li><strong>Cancelled On:</strong> {cancelled_at}</li>
            <li><strong>Cancellation Reason:</strong> {cancellation_reason or 'Customer/Admin Action'}</li>
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_refund_initiated(self, admin_email: str, admin_name: str, order_id: str, customer_name: str, refund_amount: float, refund_reason: str, initiated_at: str):
        subject = f"Refund Initiated – Order #{order_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>A refund has been initiated for order <strong>#{order_id}</strong>.</p>
        <ul>
            <li><strong>Customer:</strong> {customer_name}</li>
            <li><strong>Refund Amount:</strong> ₹{refund_amount:,.2f}</li>
            <li><strong>Reason:</strong> {refund_reason or 'N/A'}</li>
            <li><strong>Initiated On:</strong> {initiated_at}</li>
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_refund_completed(self, admin_email: str, admin_name: str, order_id: str, customer_name: str, refund_amount: float, refund_date: str):
        subject = f"Refund Completed – Order #{order_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>The refund for order <strong>#{order_id}</strong> has been completed.</p>
        <ul>
            <li><strong>Customer:</strong> {customer_name}</li>
            <li><strong>Refund Amount:</strong> ₹{refund_amount:,.2f}</li>
            <li><strong>Refund Date:</strong> {refund_date}</li>
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_low_stock(self, admin_email: str, admin_name: str, product_name: str, product_sku: str, current_stock: int, threshold: int = 10):
        subject = f"Low Stock Alert – {product_name}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>A product has reached its low-stock threshold.</p>
        <ul>
            <li><strong>Product:</strong> {product_name}</li>
            <li><strong>SKU:</strong> {product_sku}</li>
            <li><strong>Current Stock:</strong> {current_stock}</li>
            <li><strong>Low Stock Threshold:</strong> {threshold}</li>
        </ul>
        <p>Please review the inventory.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_out_of_stock(self, admin_email: str, admin_name: str, product_name: str, product_sku: str, updated_at: str):
        subject = f"Out of Stock – {product_name}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>The following product is now out of stock.</p>
        <ul>
            <li><strong>Product:</strong> {product_name}</li>
            <li><strong>SKU:</strong> {product_sku}</li>
            <li><strong>Current Stock:</strong> 0</li>
            <li><strong>Updated On:</strong> {updated_at}</li>
        </ul>
        <p>Please review the inventory and restock when required.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_offline_sale(self, admin_email: str, admin_name: str, transaction_id: str, company_name: str, transaction_amount: float, payment_method: str, transaction_date: str):
        subject = f"New Offline Sale – #{transaction_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>A new offline sale transaction has been created.</p>
        <ul>
            <li><strong>Transaction ID:</strong> #{transaction_id}</li>
            <li><strong>Company:</strong> {company_name}</li>
            <li><strong>Amount:</strong> ₹{transaction_amount:,.2f}</li>
            <li><strong>Payment Method:</strong> {payment_method}</li>
            <li><strong>Transaction Date:</strong> {transaction_date}</li>
        </ul>
        <p>Please review the transaction in Offline Sales.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_offline_sale_update(self, admin_email: str, admin_name: str, transaction_id: str, company_name: str, transaction_amount: float, status: str, updated_at: str):
        subject = f"Offline Sale {status.capitalize()} – #{transaction_id}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>An offline sale transaction has been {status}.</p>
        <ul>
            <li><strong>Transaction ID:</strong> #{transaction_id}</li>
            <li><strong>Company:</strong> {company_name}</li>
            <li><strong>Amount:</strong> ₹{transaction_amount:,.2f}</li>
            <li><strong>Updated On:</strong> {updated_at}</li>
        </ul>
        <p>Please review the transaction details.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_support_request(self, admin_email: str, admin_name: str, customer_name: str, customer_email: str, support_subject: str, support_message: str, created_at: str):
        subject = "New Customer Support Request"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>A new customer support request has been received.</p>
        <ul>
            <li><strong>Customer:</strong> {customer_name}</li>
            <li><strong>Email:</strong> {customer_email}</li>
            <li><strong>Subject:</strong> {support_subject}</li>
            <li><strong>Request:</strong> {support_message}</li>
            <li><strong>Received On:</strong> {created_at}</li>
        </ul>
        <p>Please review and respond from the Support section.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_product_alert(self, admin_email: str, admin_name: str, product_name: str, product_sku: str, alert_message: str, alert_date: str):
        subject = f"Product Alert – {product_name}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>An important product alert requires your attention.</p>
        <ul>
            <li><strong>Product:</strong> {product_name}</li>
            <li><strong>SKU:</strong> {product_sku}</li>
            <li><strong>Alert:</strong> {alert_message}</li>
            <li><strong>Date:</strong> {alert_date}</li>
        </ul>
        <p>Please review the product from the Admin Dashboard.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    async def send_admin_coupon_alert(self, admin_email: str, admin_name: str, coupon_code: str, coupon_name: str, alert_message: str, alert_date: str):
        subject = f"Coupon Alert – {coupon_code}"
        html = f"""
        <p>Hello {admin_name},</p>
        <p>An important coupon alert requires your attention.</p>
        <ul>
            <li><strong>Coupon:</strong> {coupon_code}</li>
            <li><strong>Coupon Name:</strong> {coupon_name}</li>
            <li><strong>Alert:</strong> {alert_message}</li>
            <li><strong>Date:</strong> {alert_date}</li>
        </ul>
        <p>Please review the coupon details from the Admin Dashboard.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(admin_email, subject, html)

    # ==========================================================
    # 3. CUSTOMER EMAIL NOTIFICATIONS
    # ==========================================================

    async def send_welcome(self, email: str, name: str):
        subject = f"Welcome to {self.platform_name}"
        html = f"""
        <p>Hello {name},</p>
        <p>Welcome to {self.platform_name}!</p>
        <p>Your account has been created successfully.</p>
        <p><strong>Email:</strong> {email}</p>
        <p>We are happy to have you with us.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_order_confirmation(self, email: str, name: str, order_id: str, total: float, order_date: str = "", payment_status: str = "Paid"):
        subject = f"Order Confirmed – #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Thank you for your order!</p>
        <p>Your order has been placed successfully.</p>
        <ul>
            <li><strong>Order ID:</strong> #{order_id}</li>
            <li><strong>Order Date:</strong> {order_date or 'Today'}</li>
            <li><strong>Total Amount:</strong> ₹{total:,.2f}</li>
            <li><strong>Payment Status:</strong> {payment_status}</li>
        </ul>
        <p>We will keep you updated about your order.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_payment_successful(self, email: str, name: str, order_id: str, amount: float, payment_method: str, payment_date: str):
        subject = f"Payment Successful – Order #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Your payment for order <strong>#{order_id}</strong> was successful.</p>
        <ul>
            <li><strong>Amount Paid:</strong> ₹{amount:,.2f}</li>
            <li><strong>Payment Method:</strong> {payment_method}</li>
            <li><strong>Payment Date:</strong> {payment_date}</li>
        </ul>
        <p>Thank you for your purchase.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_payment_failed(self, email: str, name: str, order_id: str, amount: float, failure_reason: str):
        subject = f"Payment Failed – Order #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Unfortunately, your payment for order <strong>#{order_id}</strong> was unsuccessful.</p>
        <ul>
            <li><strong>Amount:</strong> ₹{amount:,.2f}</li>
            <li><strong>Reason:</strong> {failure_reason or 'Transaction declined'}</li>
        </ul>
        <p>Please try again or use another payment method if applicable.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_order_processing(self, email: str, name: str, order_id: str):
        subject = f"Your Order Is Being Processed – #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Your order <strong>#{order_id}</strong> is now being processed.</p>
        <p>We will notify you when your order is shipped.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_shipping_update(self, email: str, name: str, order_id: str, tracking_number: str, courier_name: str = "Standard Shipping", estimated_delivery: str = "3-5 Business Days"):
        subject = f"Your Order Has Been Shipped – #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Good news! Your order <strong>#{order_id}</strong> has been shipped.</p>
        <ul>
            <li><strong>Tracking Number:</strong> {tracking_number}</li>
            <li><strong>Courier:</strong> {courier_name}</li>
            <li><strong>Estimated Delivery:</strong> {estimated_delivery}</li>
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_out_for_delivery(self, email: str, name: str, order_id: str, estimated_delivery: str = "Today"):
        subject = f"Your Order Is Out for Delivery – #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Your order <strong>#{order_id}</strong> is out for delivery.</p>
        <p><strong>Estimated Delivery:</strong> {estimated_delivery}</p>
        <p>Please keep your delivery details available.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_order_delivered(self, email: str, name: str, order_id: str, delivered_at: str):
        subject = f"Order Delivered – #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Your order <strong>#{order_id}</strong> has been delivered successfully.</p>
        <p><strong>Delivered On:</strong> {delivered_at}</p>
        <p>Thank you for shopping with us.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_cancellation(self, email: str, name: str, order_id: str, cancellation_reason: str = "Customer Request", order_total: float = 0.0):
        subject = f"Order Cancelled – #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Your order <strong>#{order_id}</strong> has been cancelled.</p>
        <ul>
            <li><strong>Cancellation Reason:</strong> {cancellation_reason}</li>
            {f'<li><strong>Order Amount:</strong> ₹{order_total:,.2f}</li>' if order_total > 0 else ''}
        </ul>
        <p>If a refund is applicable, you will receive a separate update.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_refund_initiated(self, email: str, name: str, order_id: str, refund_amount: float, initiated_at: str):
        subject = f"Refund Initiated – Order #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Your refund has been initiated for order <strong>#{order_id}</strong>.</p>
        <ul>
            <li><strong>Refund Amount:</strong> ₹{refund_amount:,.2f}</li>
            <li><strong>Initiated On:</strong> {initiated_at}</li>
        </ul>
        <p>You will receive another notification once the refund is completed.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_refund_notification(self, email: str, name: str, order_id: str, amount: float, refund_date: str = "", refund_reference: str = ""):
        subject = f"Refund Completed – Order #{order_id}"
        html = f"""
        <p>Hello {name},</p>
        <p>Your refund for order <strong>#{order_id}</strong> has been completed.</p>
        <ul>
            <li><strong>Refund Amount:</strong> ₹{amount:,.2f}</li>
            {f'<li><strong>Refund Date:</strong> {refund_date}</li>' if refund_date else ''}
            {f'<li><strong>Refund Reference:</strong> {refund_reference}</li>' if refund_reference else ''}
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_coins_credited(self, email: str, name: str, coins_earned: int, coin_balance: int, credited_at: str):
        subject = "Coins Credited to Your Account"
        html = f"""
        <p>Hello {name},</p>
        <p><strong>{coins_earned}</strong> coins have been credited to your account.</p>
        <ul>
            <li><strong>Current Coin Balance:</strong> {coin_balance}</li>
            <li><strong>Credited On:</strong> {credited_at}</li>
        </ul>
        <p>Thank you for shopping with us.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_coins_used(self, email: str, name: str, coins_used: int, coin_balance: int, order_id: str):
        subject = "Coins Used Successfully"
        html = f"""
        <p>Hello {name},</p>
        <p><strong>{coins_used}</strong> coins were used for your purchase.</p>
        <ul>
            <li><strong>Remaining Coin Balance:</strong> {coin_balance}</li>
            <li><strong>Order ID:</strong> #{order_id}</li>
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_coins_restored(self, email: str, name: str, coins_restored: int, coin_balance: int, restored_at: str):
        subject = "Coins Restored to Your Account"
        html = f"""
        <p>Hello {name},</p>
        <p><strong>{coins_restored}</strong> coins have been restored to your account.</p>
        <ul>
            <li><strong>Current Coin Balance:</strong> {coin_balance}</li>
            <li><strong>Restored On:</strong> {restored_at}</li>
        </ul>
        <br/>
        <p>Regards,<br/>{self.platform_name} Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_ticket_created(self, email: str, name: str, ticket_id: str, category: str, description: str, created_at: str = ""):
        subject = "Support Request Received"
        html = f"""
        <p>Hello {name},</p>
        <p>We have received your support request.</p>
        <ul>
            <li><strong>Ticket ID:</strong> #{ticket_id[:8]}</li>
            <li><strong>Subject:</strong> {category}</li>
            {f'<li><strong>Created On:</strong> {created_at}</li>' if created_at else ''}
        </ul>
        <p>Our team will review your request and respond as soon as possible.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Support Team</p>
        """
        return await self.send_email(email, subject, html)

    async def send_ticket_updated(self, email: str, name: str, ticket_id: str, support_subject: str, status: str, support_response: str):
        subject = f"Update on Support Request #{ticket_id[:8]}"
        html = f"""
        <p>Hello {name},</p>
        <p>There is an update to your support request.</p>
        <ul>
            <li><strong>Ticket ID:</strong> #{ticket_id[:8]}</li>
            <li><strong>Subject:</strong> {support_subject}</li>
            <li><strong>Status:</strong> {status}</li>
        </ul>
        <p><strong>Response:</strong><br/>{support_response}</p>
        <p>Please log in to your account for further details.</p>
        <br/>
        <p>Regards,<br/>{self.platform_name} Support Team</p>
        """
        return await self.send_email(email, subject, html)


resend_email = ResendEmailIntegration()
