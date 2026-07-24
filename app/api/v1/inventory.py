from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.inventory import InventoryLogResponse, StockUpdatePayload
from app.schemas.product import ProductResponse
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])


@router.post("/update", response_model=ProductResponse, summary="Update stock level (admin only)")
async def update_stock(
    payload: StockUpdatePayload,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = InventoryService(db)
        return await service.update_stock(payload, performed_by_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/low-stock", response_model=list[ProductResponse], summary="Get low stock alerts (admin only)")
async def get_low_stock(
    threshold: int = Query(default=10, ge=1),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = InventoryService(db)
    return await service.get_low_stock_products(threshold=threshold)


@router.get("/logs/{product_id}", response_model=list[InventoryLogResponse], summary="Get inventory log history for a product (admin only)")
async def get_inventory_logs(
    product_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = InventoryService(db)
    return await service.get_inventory_logs(product_id)
