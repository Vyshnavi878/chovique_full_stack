import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.razorpay import razorpay_client
from app.repositories.address_repository import AddressRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.coupon_repository import CouponRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderPayload, OrderResponse, ShippingAddressSchema

logger = logging.getLogger(__name__)


class CheckoutService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cart_repo = CartRepository(db)
        self.product_repo = ProductRepository(db)
        self.coupon_repo = CouponRepository(db)
        self.address_repo = AddressRepository(db)
        self.order_repo = OrderRepository(db)
        self.payment_repo = PaymentRepository(db)

    async def initiate_checkout(
        self,
        user_id: str,
        payload: OrderPayload,
    ) -> Dict[str, Any]:
        """
        100% server-side checkout engine.
        1. Validate stock & live prices for all items.
        2. Validate shipping address.
        3. Validate coupon conditions (expiry, min order, max discount).
        4. Calculate tax & shipping costs.
        5. Create Pending Order in database.
        6. Initiate Razorpay Order & register Payment attempt.
        7. Return Razorpay Order ID & checkout summary to client.
        """
        logger.info("Initiating checkout for user %s", user_id)

        if not payload.items:
            raise ValueError("Checkout items list cannot be empty.")

        subtotal = 0.0
        items_data = []

        # Step 1: Validate stock & prices server-side
        for item in payload.items:
            product = await self.product_repo.get_by_id(item.product_id)
            if not product or not product.is_active:
                raise ValueError(f"Product '{item.product_id}' is unavailable.")

            if product.stock < item.quantity:
                raise ValueError(f"Insufficient stock for '{product.name}'. Only {product.stock} left.")

            unit_price = product.price
            subtotal += unit_price * item.quantity
            items_data.append({
                "product_id": product.id,
                "quantity": item.quantity,
                "price": unit_price,
            })

        # Step 2: Validate coupon server-side
        discount = 0.0
        if payload.coupon_code:
            coupon = await self.coupon_repo.get_by_code(payload.coupon_code)
            now_utc = datetime.now(timezone.utc)
            if (
                coupon
                and coupon.is_active
                and (coupon.expires_at is None or coupon.expires_at > now_utc)
            ):
                # Check min order value if applicable
                if coupon.discount_percent > 0:
                    discount = (subtotal * coupon.discount_percent) / 100.0
                elif coupon.discount_amount > 0:
                    discount = coupon.discount_amount

        # Step 3: Calculate shipping & tax
        shipping = 0.0 if subtotal > 1500 else 99.0
        tax = round(subtotal * 0.05, 2)  # 5% GST
        total = max(0.0, subtotal - discount + shipping + tax)

        total_rounded = round(total, 2)

        # Step 4: Create Pending Order in DB
        shipping_addr_dict = payload.shipping_address.model_dump()
        order = await self.order_repo.create_order(
            user_id=user_id,
            total=total_rounded,
            subtotal=round(subtotal, 2),
            discount=round(discount, 2),
            shipping=round(shipping, 2),
            tax=round(tax, 2),
            shipping_address=shipping_addr_dict,
            delivery_option=payload.delivery_option,
            payment_method=payload.payment_method,
            items_data=items_data,
        )

        # Step 5: Initiate Razorpay Order
        razorpay_order = razorpay_client.create_order(
            amount=total_rounded,
            currency="INR",
            receipt=order.id,
            notes={"user_id": user_id, "order_id": order.id},
        )

        # Step 6: Create Payment record in DB
        payment = await self.payment_repo.create_payment(
            order_id=order.id,
            user_id=user_id,
            razorpay_order_id=razorpay_order.get("id"),
            amount=total_rounded,
            currency="INR",
        )

        return {
            "order_id": order.id,
            "razorpay_order_id": razorpay_order.get("id"),
            "amount": total_rounded,
            "currency": "INR",
            "key_id": razorpay_client.key_id,
            "subtotal": subtotal,
            "discount": discount,
            "shipping": shipping,
            "tax": tax,
        }
