from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inventory import InventoryLog


class InventoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_change(
        self,
        product_id: str,
        change_quantity: int,
        reason: str,
        notes: str | None = None,
        performed_by: str | None = None,
    ) -> InventoryLog:
        log_entry = InventoryLog(
            product_id=product_id,
            change_quantity=change_quantity,
            reason=reason,
            notes=notes,
            performed_by=performed_by,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_logs_for_product(self, product_id: str) -> list[InventoryLog]:
        result = await self.db.execute(
            select(InventoryLog)
            .where(InventoryLog.product_id == product_id)
            .order_by(InventoryLog.created_at.desc())
        )
        return list(result.scalars().all())
