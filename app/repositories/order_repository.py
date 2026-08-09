from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem


class OrderRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(
        self,
        user_id: str,
        total: float,
        subtotal: float,
        discount: float,
        shipping: float,
        tax: float,
        shipping_address: dict,
        delivery_option: str,
        payment_method: str,
        items_data: list[dict],
        coupon_code: str | None = None,
        coupon_discount: float = 0.0,
        coins_used: int = 0,
        coin_discount: float = 0.0,
        coins_earned: int = 0,
        commit: bool = True,
    ) -> Order:
        order = Order(
            user_id=user_id,
            total=total,
            subtotal=subtotal,
            discount=discount,
            coupon_code=coupon_code,
            coupon_discount=coupon_discount,
            coins_used=coins_used,
            coin_discount=coin_discount,
            coins_earned=coins_earned,
            shipping=shipping,
            tax=tax,
            shipping_address=shipping_address,
            delivery_option=delivery_option,
            payment_method=payment_method,
            status="Processing",
        )
        self.db.add(order)
        await self.db.flush()

        for item_info in items_data:
            item = OrderItem(
                order_id=order.id,
                product_id=item_info["product_id"],
                quantity=item_info["quantity"],
                price=item_info["price"],
            )
            self.db.add(item)

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        # Re-fetch with loaded items and product relationships
        return await self.get_by_id(order.id)

    async def get_user_orders(self, user_id: str) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, order_id: str) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product)
            )
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
