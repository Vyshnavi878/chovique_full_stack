from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offline_sale import OfflineSale


class OfflineSaleRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[OfflineSale]:
        result = await self.db.execute(
            select(OfflineSale).order_by(OfflineSale.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        product_name: str,
        quantity: int,
        total_price: float,
        payment_method: str,
    ) -> OfflineSale:
        sale = OfflineSale(
            product_name=product_name,
            quantity=quantity,
            total_price=total_price,
            payment_method=payment_method,
        )
        self.db.add(sale)
        await self.db.commit()
        await self.db.refresh(sale)
        return sale

    async def bulk_create(self, sales: list[dict]) -> tuple[int, int]:
        """Bulk insert offline sales. Returns (imported, skipped)."""
        imported = 0
        skipped = 0
        for sale_data in sales:
            try:
                sale = OfflineSale(
                    product_name=sale_data.get("product_name", ""),
                    quantity=int(sale_data.get("quantity", 1)),
                    total_price=float(sale_data.get("total_price", 0)),
                    payment_method=sale_data.get("payment_method", "Cash"),
                )
                self.db.add(sale)
                imported += 1
            except Exception:
                skipped += 1
        if imported > 0:
            await self.db.commit()
        return imported, skipped
