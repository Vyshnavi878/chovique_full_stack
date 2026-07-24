import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.admin import (
    BannerImageResponse,
    DashboardStatsResponse,
    ImportSalesResponse,
    OfflineSalePayload,
    OfflineSaleResponse,
    ResolveTicketPayload,
    UpdateOrderStatusPayload,
)
from app.schemas.order import OrderResponse
from app.schemas.ticket import SupportTicketResponse
from app.schemas.user import SystemUserResponse
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Module"])


# ======================================================
# DASHBOARD STATS
# ======================================================

@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get admin dashboard analytics stats",
)
async def get_dashboard_stats(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_dashboard_stats()


# ======================================================
# ORDERS (admin — all orders site-wide)
# ======================================================

@router.get(
    "/orders",
    response_model=list[OrderResponse],
    summary="Get all orders site-wide (admin only)",
)
async def get_all_orders(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_all_orders()


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status (admin only)",
)
async def update_order_status(
    order_id: str,
    payload: UpdateOrderStatusPayload,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    order = await service.update_order_status(order_id, payload, admin_id=current_user.id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


# ======================================================
# USERS (admin)
# ======================================================

@router.get(
    "/users",
    response_model=list[SystemUserResponse],
    summary="Get all registered users (admin only)",
)
async def get_all_users(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_all_users()


# ======================================================
# SUPPORT TICKETS (admin — all tickets site-wide)
# ======================================================

@router.get(
    "/tickets",
    response_model=list[SupportTicketResponse],
    summary="Get all support tickets site-wide (admin only)",
)
async def get_all_tickets(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_all_tickets()


@router.post(
    "/tickets/{ticket_id}/resolve",
    response_model=SupportTicketResponse,
    summary="Resolve a support ticket (admin only)",
)
async def resolve_ticket(
    ticket_id: str,
    payload: ResolveTicketPayload,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    ticket = await service.resolve_ticket(ticket_id, payload, admin_id=current_user.id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return ticket


# ======================================================
# OFFLINE SALES
# ======================================================

@router.get(
    "/offline-sales",
    response_model=list[OfflineSaleResponse],
    summary="Get all offline (POS) sales records (admin only)",
)
async def get_offline_sales(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_offline_sales()


@router.post(
    "/offline-sales",
    response_model=OfflineSaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually log a single offline sale (admin only)",
)
async def add_offline_sale(
    payload: OfflineSalePayload,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.add_offline_sale(payload)


@router.post(
    "/offline-sales/import",
    response_model=ImportSalesResponse,
    summary="Bulk import offline sales from a CSV file (admin only)",
)
async def import_offline_sales(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    service = AdminService(db)
    return await service.import_offline_sales_csv(content)


# ======================================================
# BANNER IMAGE UPLOAD (superadmin)
# ======================================================

@router.post(
    "/banners/{banner_id}/image",
    response_model=BannerImageResponse,
    summary="Upload a banner hero image (superadmin only)",
)
async def upload_banner_image(
    banner_id: str,
    image: UploadFile = File(...),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    content = await image.read()
    service = AdminService(db)
    image_url = await service.upload_banner_image(banner_id, content, image.filename or "banner.jpg")
    return BannerImageResponse(image_url=image_url)
