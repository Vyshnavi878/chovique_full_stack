from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.cart import Cart, CartItem


class CartRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_user_cart(self, user_id: str) -> Cart:
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.user_id == user_id)
        )
        cart = result.scalar_one_or_none()

        if not cart:
            cart = Cart(user_id=user_id)
            self.db.add(cart)
            await self.db.commit()
            await self.db.refresh(cart)
            # Fetch with loaded relationships
            result = await self.db.execute(
                select(Cart)
                .options(selectinload(Cart.items).selectinload(CartItem.product))
                .where(Cart.id == cart.id)
            )
            cart = result.scalar_one_or_none()

        return cart

    async def add_or_update_item(self, cart_id: str, product_id: str, quantity: int = 1) -> CartItem:
        result = await self.db.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        )
        item = result.scalar_one_or_none()

        if item:
            item.quantity += quantity
        else:
            item = CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity)
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_item_quantity(self, cart_id: str, product_id: str, quantity: int) -> bool:
        if quantity <= 0:
            return await self.remove_item(cart_id, product_id)

        result = await self.db.execute(
            update(CartItem)
            .where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
            .values(quantity=quantity)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def remove_item(self, cart_id: str, product_id: str) -> bool:
        result = await self.db.execute(
            delete(CartItem)
            .where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def clear_cart(self, cart_id: str) -> None:
        await self.db.execute(
            delete(CartItem).where(CartItem.cart_id == cart_id)
        )
        await self.db.commit()
