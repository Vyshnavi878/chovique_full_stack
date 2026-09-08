import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from app.services.mail_service import MailService
from app.integrations.resend import resend_email

async def main():
    print("Testing Registration OTP dispatch...")
    await MailService.send_registration_otp(
        email="chovique25@gmail.com",
        otp="948215",
        name="Avinash",
    )
    print("Registration OTP dispatched!")

    print("Testing Luxury Order Confirmation dispatch...")
    await resend_email.send_order_confirmation(
        email="chovique25@gmail.com",
        name="Avinash",
        order_id="CHV-98721",
        total=2450.00,
        order_date="08 Sept 2026",
        payment_status="Paid",
        payment_method="UPI / Razorpay",
        items_html="""
        <li><strong>Dark Truffle Noir (75% Cacao)</strong> &times; 1 &mdash; ₹850.00</li>
        <li><strong>Velvet Hazelnut Praline Box</strong> &times; 1 &mdash; ₹1,100.00</li>
        <li><strong>Artisanal Sea Salt Caramel Bar</strong> &times; 2 &mdash; ₹500.00</li>
        """,
        delivery_option="Express Climate-Controlled Courier",
    )
    print("Order Confirmation dispatched!")

if __name__ == "__main__":
    asyncio.run(main())
