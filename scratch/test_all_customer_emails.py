import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from app.integrations.resend import resend_email

async def main():
    print("Testing Welcome Email...")
    await resend_email.send_welcome("chovique25@gmail.com", "Avinash")

    print("Testing Shipping Update...")
    await resend_email.send_shipping_update(
        email="chovique25@gmail.com",
        name="Avinash",
        order_id="CHV-98721",
        tracking_number="CHV-BLR-884920",
        courier_name="BlueDart Luxury Express",
        estimated_delivery="10 Sept 2026",
    )

    print("Testing Out For Delivery...")
    await resend_email.send_out_for_delivery("chovique25@gmail.com", "Avinash", "CHV-98721", "Today by 4:00 PM")

    print("Testing Order Delivered...")
    await resend_email.send_order_delivered(
        email="chovique25@gmail.com",
        name="Avinash",
        order_id="CHV-98721",
        delivered_at="08 Sept 2026, 3:45 PM",
        payment_method="UPI",
        payment_status="Paid",
        order_total=2450.0,
    )

    print("Testing Coins Credited...")
    await resend_email.send_coins_credited("chovique25@gmail.com", "Avinash", 120, 350, "08 Sept 2026")

    print("ALL TEST CUSTOMER EMAILS DISPATCHED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
