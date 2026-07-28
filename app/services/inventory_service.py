import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.inventory import InventoryLogResponse, StockUpdatePayload
from app.schemas.product import ProductResponse

logger = logging.getLogger(__name__)


class InventoryService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)

    async def update_stock(
        self,
        payload: StockUpdatePayload,
        performed_by_id: Optional[str] = None,
    ) -> ProductResponse:

        product = await self.product_repo.get_by_id(payload.product_id)
        if not product:
            raise ValueError("Product not found.")

        if payload.new_stock is not None:
            new_stock = max(0, payload.new_stock)
            change = new_stock - product.stock
        else:
            change = payload.change_quantity or 0
            new_stock = max(0, product.stock + change)

        updated_product = await self.product_repo.update(product.id, stock=new_stock)

        await self.inventory_repo.log_change(
            product_id=product.id,
            change_quantity=change,
            reason=payload.reason or "restock",
            notes=payload.notes,
            performed_by=performed_by_id,
        )

        logger.info(
            "Stock updated for product %s: old=%d, change=%d, new=%d",
            product.id,
            product.stock,
            change,
            new_stock,
        )


        return ProductResponse.from_orm_model(updated_product)

    async def get_low_stock_products(self, threshold: int = 10) -> list[ProductResponse]:
        all_products = await self.product_repo.get_all(per_page=1000)
        low_stock = [p for p in all_products["items"] if p.stock <= threshold]
        return [ProductResponse.from_orm_model(p) for p in low_stock]

    async def get_inventory_logs(self, product_id: str) -> list[InventoryLogResponse]:
        logs = await self.inventory_repo.get_logs_for_product(product_id)
        return [
            InventoryLogResponse(
                id=l.id,
                product_id=l.product_id,
                change_quantity=l.change_quantity,
                reason=l.reason,
                notes=l.notes,
                created_at=l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else "",
            )
            for l in logs
        ]
