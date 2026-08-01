import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.admin import (
    AuditLogEntry,
    BannerImageResponse,
    CreateAdminRequest,
    CreateBannerRequest,
    CreateReelRequest,
    CreateTestimonialRequest,
    DashboardStatsResponse,
    ImportSalesResponse,
    OfflineSalePayload,
    OfflineSaleResponse,
    ReelResponse,
    ResolveTicketPayload,
    SetContactRequest,
    SetStatsRequest,
    UpdateAdminPasswordPayload,
    UpdateAdminRequest,
    UpdateOrderStatusPayload,
)
from app.schemas.home import BannerResponse, ContactInfoResponse, StatsResponse, TestimonialResponse
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
    "/audit-logs",
    response_model=list[AuditLogEntry],
    summary="Get recent audit log entries (superadmin only)",
)
async def get_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_audit_logs(limit=limit)


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


@router.post(
    "/users",
    response_model=SystemUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new administrator user (superadmin only)",
)
async def create_admin(
    payload: CreateAdminRequest,
    current_user: User = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = AdminService(db)
        return await service.create_admin(payload, superadmin_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete/Revoke a user (superadmin only)",
)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    success = await service.delete_user(user_id, superadmin_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return None


@router.patch(
    "/users/{user_id}",
    response_model=SystemUserResponse,
    summary="Update an administrator's details (superadmin only)",
)
async def update_admin(
    user_id: str,
    payload: UpdateAdminRequest,
    current_user: User = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = AdminService(db)
        updated = await service.update_admin(user_id, payload, superadmin_id=current_user.id)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator user not found.")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/users/{user_id}/password",
    summary="Update an administrator password (superadmin only)",
)
async def update_admin_password(
    user_id: str,
    payload: UpdateAdminPasswordPayload,
    current_user: User = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    success = await service.update_admin_password(user_id, payload.password, superadmin_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator user not found.")
    return {"message": "Administrator password updated successfully."}


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
    service = AdminService(db)
    image_url = await service.upload_banner_image(banner_id, image_file=image)
    return BannerImageResponse(image_url=image_url)


# ======================================================
# CMS — BANNERS
# ======================================================

@router.post(
    "/banners",
    response_model=BannerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new banner (admin only)",
)
async def create_banner(
    title: str = Form(...),
    subtitle: Optional[str] = Form(default=None),
    tag: Optional[str] = Form(default=None),
    button_text: Optional[str] = Form(default=None),
    link: Optional[str] = Form(default=None),
    sort_order: int = Form(default=0),
    is_active: bool = Form(default=True),
    image: UploadFile = File(default=None),
    image_url: Optional[str] = Form(default=None),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    payload = CreateBannerRequest(
        title=title,
        subtitle=subtitle,
        tag=tag,
        image=image_url,
        button_text=button_text,
        link=link,
        sort_order=sort_order,
        is_active=is_active,
    )
    service = AdminService(db)
    return await service.create_banner(payload, image_file=image)


@router.delete(
    "/banners/{banner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a banner (superadmin only)",
)
async def delete_banner(
    banner_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    success = await service.delete_banner(banner_id, superadmin_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner not found.")
    return None


# ======================================================
# CMS — TESTIMONIALS
# ======================================================

@router.post(
    "/testimonials",
    response_model=TestimonialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new testimonial (admin only)",
)
async def create_testimonial(
    author: str = Form(...),
    title: Optional[str] = Form(default=None),
    text: str = Form(...),
    rating: float = Form(default=5.0),
    initials: Optional[str] = Form(default=None),
    avatar_url: Optional[str] = Form(default=None),
    is_active: bool = Form(default=True),
    sort_order: int = Form(default=0),
    avatar: UploadFile = File(default=None),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    payload = CreateTestimonialRequest(
        author=author,
        title=title,
        text=text,
        rating=rating,
        initials=initials,
        avatar_url=avatar_url,
        is_active=is_active,
        sort_order=sort_order,
    )
    service = AdminService(db)
    return await service.create_testimonial(payload, avatar_file=avatar)


# ======================================================
# CMS — INSTAGRAM REELS
# ======================================================

@router.post(
    "/reels",
    response_model=ReelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Instagram reel entry (admin only)",
)
async def create_reel(
    title: str = Form(...),
    likes: str = Form(default="0"),
    comments: str = Form(default="0"),
    views: str = Form(default="0 views"),
    sort_order: int = Form(default=0),
    is_active: bool = Form(default=True),
    video_url: Optional[str] = Form(default=None),
    video: UploadFile = File(default=None),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    payload = CreateReelRequest(
        video_url=video_url,
        likes=likes,
        comments=comments,
        views=views,
        title=title,
        sort_order=sort_order,
        is_active=is_active,
    )
    service = AdminService(db)
    return await service.create_reel(payload, video_file=video)


@router.delete(
    "/reels/{reel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an Instagram reel (admin only)",
)
async def delete_reel(
    reel_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    success = await service.delete_reel(reel_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    return None


# ======================================================
# CMS — TESTIMONIALS
# ======================================================

@router.post(
    "/testimonials",
    response_model=TestimonialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer testimonial (admin only)",
)
async def create_testimonial(
    author: str = Form(...),
    title: str = Form(...),
    text: str = Form(...),
    rating: float = Form(default=5.0),
    initials: Optional[str] = Form(default=None),
    avatar_url: Optional[str] = Form(default=None),
    avatar: UploadFile = File(default=None),
    sort_order: int = Form(default=0),
    is_active: bool = Form(default=True),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    payload = CreateTestimonialRequest(
        author=author,
        title=title,
        text=text,
        rating=rating,
        initials=initials or author[:2].upper(),
        avatar_url=avatar_url,
        sort_order=sort_order,
        is_active=is_active,
    )
    service = AdminService(db)
    return await service.create_testimonial(payload, avatar_file=avatar)


@router.delete(
    "/testimonials/{testimonial_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a customer testimonial (admin only)",
)
async def delete_testimonial(
    testimonial_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    success = await service.delete_testimonial(testimonial_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Testimonial not found.")
    return None


# ======================================================
# CMS — SITE CONFIG (STATS / CONTACT)
# ======================================================

@router.put(
    "/config/stats",
    response_model=StatsResponse,
    summary="Set home page site stats (admin only)",
)
@router.patch(
    "/config/stats",
    response_model=StatsResponse,
    summary="Set home page site stats (admin only)",
)
async def set_stats(
    payload: SetStatsRequest,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.set_stats(payload)


@router.put(
    "/config/contact",
    response_model=ContactInfoResponse,
    summary="Set home page contact info (admin only)",
)
@router.patch(
    "/config/contact",
    response_model=ContactInfoResponse,
    summary="Set home page contact info (admin only)",
)
async def set_contact(
    payload: SetContactRequest,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.set_contact(payload)


# ======================================================
# CONTACT FORM MESSAGES (admin view)
# ======================================================

@router.get(
    "/contact-messages",
    summary="Get all submitted contact messages (admin only)",
)
async def get_contact_messages(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_contact_messages()


@router.delete(
    "/contact-messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contact message (admin only)",
)
async def delete_contact_message(
    message_id: str,
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    deleted = await service.delete_contact_message(message_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    return None


# ======================================================
# OUR STORY CRAFTING VIDEO UPLOAD
# ======================================================

@router.post(
    "/story-video",
    summary="Upload Our Story crafting video (admin only)",
)
async def upload_story_video(
    video: UploadFile = File(...),
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    video_url = await service.upload_story_video(video)
    return {"video_url": video_url}


@router.delete(
    "/story-video",
    summary="Delete / reset Our Story crafting video (admin only)",
)
async def delete_story_video(
    current_user: User = Depends(require_role("admin", "superadmin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    video_url = await service.delete_story_video()
    return {"video_url": video_url}
