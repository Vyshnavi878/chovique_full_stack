from typing import Optional
from pydantic import BaseModel, ConfigDict


class StockUpdatePayload(BaseModel):
    product_id: str
    change_quantity: int
    reason: str = "restock"  # 'restock', 'sale', 'adjustment', 'return'
    notes: Optional[str] = None


class InventoryLogResponse(BaseModel):
    id: str
    product_id: str
    change_quantity: int
    reason: str
    notes: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)
