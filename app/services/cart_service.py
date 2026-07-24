import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import CartItemResponseSchema, CartResponseSchema
from app.schemas.product import ProductResponse

logger = logging.getLogger(__name__)


class CartService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cart_repo = CartRepository(db)
        self.product_repo = ProductRepository(db)

    async def get_cart(self, user_id: str) -> CartResponseSchema:
        """
        Fetch cart and recalculate subtotal and item count on EVERY request.
        Validates product availability and latest price.
        """
        cart = await self.cart_repo.get_or_create_user_cart(user_id)

        items_response = []
        subtotal = 0.0
        item_count = 0

        for item in cart.items:
            product = item.product
            # Validate product is active
            if product and product.is_active:
                prod_res = ProductResponse.from_orm_model(product)
                subtotal += product.price * item.quantity
                item_count += item.quantity
                items_response.append(
                    CartItemResponseSchema(
                        id=item.id,
                        product=prod_res,
                        quantity=item.quantity,
                    )
                )

        return CartResponseSchema(
            id=cart.id,
            items=items_response,
            subtotal=round(subtotal, 2),
            item_count=item_count,
        )

    async def add_to_cart(self, user_id: str, product_id: str, quantity: int = 1) -> CartResponseSchema:
        product = await self.product_repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise ValueError("Product is not available.")

        if product.stock < quantity:
            raise ValueError(f"Insufficient stock available. Only {product.stock} items left.")

        cart = await self.cart_repo.get_or_create_user_cart(user_id)
        await self.cart_repo.add_or_update_item(cart.id, product_id, quantity)

        return await self.get_cart(user_id)

    async def update_quantity(self, user_id: str, product_id: str, quantity: int) -> CartResponseSchema:
        if quantity > 0:
            product = await self.product_repo.get_by_id(product_id)
            if not product or not product.is_active:
                raise ValueError("Product is not available.")
            if product.stock < quantity:
                raise ValueError(f"Insufficient stock available. Only {product.stock} items left.")

        cart = await self.cart_repo.get_or_create_user_cart(user_id)
        await self.cart_repo.update_item_quantity(cart.id, product_id, quantity)

        return await self.get_cart(user_id)

    async def remove_item(self, user_id: str, product_id: str) -> CartResponseSchema:
        cart = await self.cart_repo.get_or_create_user_cart(user_id)
        await self.cart_repo.remove_item(cart.id, product_id)
        return await self.get_cart(user_id)

    async def clear_cart(self, user_id: str) -> CartResponseSchema:
        cart = await self.cart_repo.get_or_create_user_cart(user_id)
        await self.cart_repo.clear_cart(cart.id)
        return await self.get_cart(user_id)
