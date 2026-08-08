import csv
import io
import logging
import os
import uuid
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.integrations.resend import resend_email
from app.models.offline_sale import OfflineSale
from app.models.order import Order
from app.models.product import Product
from app.models.ticket import SupportTicket
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.banner_repository import BannerRepository
from app.repositories.offline_sale_repository import OfflineSaleRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.reel_repository import ReelRepository
from app.repositories.site_config_repository import SiteConfigRepository
from app.repositories.testimonial_repository import TestimonialRepository
from app.repositories.ticket_repository import TicketRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AuditLogEntry,
    BannerImageResponse,
    CreateAdminRequest,
    CreateBannerRequest,
    UpdateBannerRequest,
    CreateReelRequest,
    CreateTestimonialRequest,
    DashboardStatsResponse,
    ImportSalesResponse,
    MonthlyRevenue,
    OfflineSalePayload,
    OfflineSaleResponse,
    ReelResponse,
    ResolveTicketPayload,
    SetContactRequest,
    SetStatsRequest,
    TopProduct,
    UpdateAdminPasswordPayload,
    UpdateAdminRequest,
    UpdateOrderStatusPayload,
    CustomerDetailsResponse,
)
from app.schemas.home import BannerResponse, ContactInfoResponse, StatsResponse, TestimonialResponse
from app.schemas.order import OrderResponse
from app.schemas.ticket import SupportTicketResponse
from app.schemas.user import SystemUserResponse, UserResponse
from app.services.cloudinary_service import cloudinary_service

logger = logging.getLogger(__name__)


class AdminService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.order_repo = OrderRepository(db)
        self.product_repo = ProductRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.offline_sale_repo = OfflineSaleRepository(db)
        self.banner_repo = BannerRepository(db)
        self.testimonial_repo = TestimonialRepository(db)
        self.reel_repo = ReelRepository(db)
        self.site_config_repo = SiteConfigRepository(db)

    # ==========================================================
    # Dashboard Stats
    # ==========================================================

    async def get_dashboard_stats(self) -> DashboardStatsResponse:
        from datetime import datetime, timezone, timedelta
        from calendar import month_abbr
        from sqlalchemy import extract, case

        from app.models.order import OrderItem
        from app.models.offline_sale import OfflineSale

        # --- Valid Paid/Completed Order Statuses ---
        valid_statuses = ["Paid", "Delivered", "Shipped", "Processing"]

        # --- Basic counts ---
        sales_result = await self.db.execute(
            select(func.sum(Order.total)).where(Order.status.in_(valid_statuses))
        )
        total_sales = round(sales_result.scalar() or 0.0, 2)

        orders_result = await self.db.execute(
            select(func.count()).select_from(Order).where(Order.status.in_(valid_statuses))
        )
        total_orders = orders_result.scalar() or 0

        users_result = await self.db.execute(
            select(func.count()).select_from(User).where(User.role == "customer")
        )
        total_customers = users_result.scalar() or 0

        products_result = await self.db.execute(select(func.count()).select_from(Product))
        total_products = products_result.scalar() or 0

        low_stock_result = await self.db.execute(
            select(func.count()).select_from(Product).where(Product.stock <= 10)
        )
        low_stock_products_count = low_stock_result.scalar() or 0

        from app.models.ticket import SupportTicket
        tickets_result = await self.db.execute(
            select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "Pending")
        )
        pending_tickets_count = tickets_result.scalar() or 0

        # --- Extended KPI metrics ---
        # Total units sold (valid paid/completed orders only)
        units_sold_result = await self.db.execute(
            select(func.sum(OrderItem.quantity))
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.status.in_(valid_statuses))
        )
        total_units_sold = int(units_sold_result.scalar() or 0)

        # Total inventory stock
        stock_result = await self.db.execute(select(func.sum(Product.stock)))
        total_inventory_stock = int(stock_result.scalar() or 0)

        # Online revenue (valid paid/completed orders)
        online_rev_result = await self.db.execute(
            select(func.sum(Order.total)).where(Order.status.in_(valid_statuses))
        )
        total_online_revenue = round(online_rev_result.scalar() or 0.0, 2)

        # Offline revenue
        offline_rev_result = await self.db.execute(select(func.sum(OfflineSale.total_price)))
        total_offline_revenue = round(offline_rev_result.scalar() or 0.0, 2)

        # Admin count (admin + superadmin)
        admin_count_result = await self.db.execute(
            select(func.count()).select_from(User).where(User.role.in_(["admin", "superadmin"]))
        )
        admin_count = int(admin_count_result.scalar() or 0)

        # --- Monthly revenue — last 6 months ---
        now = datetime.now(timezone.utc)
        monthly_revenue = []
        for i in range(5, -1, -1):  # 5 months ago → this month
            target = now - timedelta(days=i * 30)
            yr, mo = target.year, target.month
            label = f"{month_abbr[mo]} {yr}"

            online_mo_result = await self.db.execute(
                select(func.sum(Order.total)).where(
                    Order.status.in_(valid_statuses),
                    extract("year", Order.created_at) == yr,
                    extract("month", Order.created_at) == mo,
                )
            )
            online_mo = round(online_mo_result.scalar() or 0.0, 2)

            offline_mo_result = await self.db.execute(
                select(func.sum(OfflineSale.total_price)).where(
                    extract("year", OfflineSale.created_at) == yr,
                    extract("month", OfflineSale.created_at) == mo,
                )
            )
            offline_mo = round(offline_mo_result.scalar() or 0.0, 2)

            monthly_revenue.append(MonthlyRevenue(
                month=label,
                online_revenue=online_mo,
                offline_revenue=offline_mo,
                total=round(online_mo + offline_mo, 2),
            ))

        # --- Top 5 products by units sold ---
        from app.schemas.admin import TopProduct
        top_prod_result = await self.db.execute(
            select(
                Product.name,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
                Product.stock,
                func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), 0.0).label("revenue"),
            )
            .join(OrderItem, Product.id == OrderItem.product_id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.status.in_(valid_statuses))
            .group_by(Product.id, Product.name, Product.stock)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
        )
        top_products = [
            TopProduct(
                name=row.name,
                units_sold=int(row.units_sold),
                stock=int(row.stock),
                revenue=round(float(row.revenue), 2),
            )
            for row in top_prod_result.all()
        ]

        return DashboardStatsResponse(
            total_sales=round(total_sales, 2),
            total_orders=total_orders,
            total_customers=total_customers,
            total_products=total_products,
            low_stock_products_count=low_stock_products_count,
            pending_tickets_count=pending_tickets_count,
            total_units_sold=total_units_sold,
            total_inventory_stock=total_inventory_stock,
            total_online_revenue=total_online_revenue,
            total_offline_revenue=total_offline_revenue,
            admin_count=admin_count,
            monthly_revenue=monthly_revenue,
            top_products=top_products,
        )

    async def get_audit_logs(self, limit: int = 50) -> list:
        """Return the most recent audit log entries with user details."""
        from app.models.audit_log import AuditLog
        from app.schemas.admin import AuditLogEntry

        result = await self.db.execute(
            select(AuditLog, User.full_name, User.email)
            .outerjoin(User, AuditLog.user_id == User.id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        entries = []
        for log, full_name, email in rows:
            entries.append(AuditLogEntry(
                id=log.id,
                action=log.action,
                user_name=full_name,
                user_email=email,
                resource=log.resource,
                details=log.details,
                created_at=log.created_at.isoformat() if log.created_at else "",
            ))
        return entries

    # ==========================================================
    # Coupons
    # ==========================================================

    async def get_coupons(self):
        from app.repositories.coupon_repository import CouponRepository
        coupon_repo = CouponRepository(self.db)
        return await coupon_repo.get_all()

    async def create_coupon(self, data):
        from app.repositories.coupon_repository import CouponRepository
        coupon_repo = CouponRepository(self.db)
        return await coupon_repo.create(**data.model_dump())
        
    async def update_coupon(self, code: str, data):
        from app.repositories.coupon_repository import CouponRepository
        coupon_repo = CouponRepository(self.db)
        return await coupon_repo.update(code, **data.model_dump(exclude_unset=True))

    async def get_contact_messages(self) -> list:
        # TODO: Implement contact form submission tracking in a DB table
        # Currently returning empty list as mock
        return []

    async def delete_contact_message(self, message_id: str) -> None:
        pass

    # ==========================================================
    # Global Configs (Theme & Platform Settings)
    # ==========================================================

    async def get_config(self, key: str) -> dict | list | str | None:
        return await self.site_config_repo.get(key)

    async def set_config(self, key: str, value: dict | list | str) -> dict | list | str:
        await self.site_config_repo.set(key, value)
        return value

    async def delete_coupon(self, code: str):
        from app.repositories.coupon_repository import CouponRepository
        coupon_repo = CouponRepository(self.db)
        return await coupon_repo.delete(code)


    # ==========================================================
    # Orders
    # ==========================================================

    async def update_order_status(
        self,
        order_id: str,
        payload: UpdateOrderStatusPayload,
        admin_id: str,
    ) -> OrderResponse | None:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None

        order.status = payload.status
        await self.db.commit()

        await self.audit_repo.log(
            action="update_order_status",
            user_id=admin_id,
            resource=f"order:{order_id}",
            details=f"Order status changed to {payload.status}",
        )

        user = await self.user_repo.get_by_id(order.user_id)
        if user:
            if payload.status == "Shipped":
                await resend_email.send_shipping_update(
                    email=user.email,
                    name=user.full_name,
                    order_id=order.id,
                    tracking_number="TRACK-" + order.id[-6:],
                )
            elif payload.status == "Cancelled":
                await resend_email.send_cancellation(
                    email=user.email,
                    name=user.full_name,
                    order_id=order.id,
                )

        from app.services.customer_service import CustomerService
        cs = CustomerService(self.db)
        return cs._format_order_response(order)

    async def get_all_orders(self) -> list[OrderResponse]:
        """Get all orders site-wide (admin view)."""
        result = await self.db.execute(
            select(Order).order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        from app.services.customer_service import CustomerService
        cs = CustomerService(self.db)
        return [cs._format_order_response(o) for o in orders]

    # ==========================================================
    # Users
    # ==========================================================

    async def get_all_users(self) -> list[SystemUserResponse]:
        result = await self.db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return [SystemUserResponse.from_orm_user(u) for u in users]

    async def get_all_customers(self) -> list[SystemUserResponse]:
        result = await self.db.execute(select(User).where(User.role == "customer").order_by(User.created_at.desc()))
        users = result.scalars().all()
        return [SystemUserResponse.from_orm_user(u) for u in users]

    async def get_customer_details(self, user_id: str) -> CustomerDetailsResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.role != "customer":
            raise ValueError("Customer not found.")

        result_orders = await self.db.execute(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()))
        orders = result_orders.scalars().all()
        
        result_tickets = await self.db.execute(select(SupportTicket).where(SupportTicket.user_id == user_id).order_by(SupportTicket.created_at.desc()))
        tickets = result_tickets.scalars().all()

        from app.schemas.user import UserResponse
        from app.services.customer_service import CustomerService
        
        cs = CustomerService(self.db)
        
        return CustomerDetailsResponse(
            user=UserResponse.from_orm_user(user),
            total_spent=sum(o.total for o in orders),
            total_orders=len(orders),
            recent_orders=[cs._format_order_response(o) for o in orders[:5]],
            support_tickets=[cs._format_ticket_response(t) for t in tickets],
        )

    async def create_admin(self, payload: CreateAdminRequest, superadmin_id: str) -> SystemUserResponse:
        existing = await self.user_repo.get_by_email(payload.email)
        if existing:
            raise ValueError("User with this email already exists.")

        if payload.role not in ["admin", "superadmin"]:
            raise ValueError("Invalid role specified.")

        hashed_pw = hash_password(payload.password)
        new_admin = await self.user_repo.create(
            email=payload.email,
            hashed_password=hashed_pw,
            full_name=payload.full_name,
            role=payload.role,
            is_email_verified=True,
            is_active=True,
        )

        await self.audit_repo.log(
            action="create_admin",
            user_id=superadmin_id,
            resource=f"user:{new_admin.id}",
            details=f"Created administrator account: {payload.email}",
        )

        return SystemUserResponse.from_orm_user(new_admin)

    async def delete_user(self, user_id: str, superadmin_id: str) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False

        await self.db.delete(user)
        await self.db.commit()

        await self.audit_repo.log(
            action="delete_user",
            user_id=superadmin_id,
            resource=f"user:{user_id}",
            details=f"Deleted user account: {user.email}",
        )

        return True

    async def update_admin_password(
        self,
        user_id: str,
        new_password: str,
        superadmin_id: str,
    ) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.role not in ("admin", "superadmin"):
            return False

        hashed_pw = hash_password(new_password)
        await self.user_repo.update_password(user_id, hashed_pw)

        await self.audit_repo.log(
            action="update_admin_password",
            user_id=superadmin_id,
            resource=f"user:{user_id}",
            details=f"Updated password for administrator: {user.email}",
        )

        return True

    async def update_admin(
        self,
        user_id: str,
        payload,
        superadmin_id: str,
    ):
        """Update admin full_name and/or email (superadmin only)."""
        from app.schemas.user import SystemUserResponse
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.role not in ("admin", "superadmin"):
            return None

        changes = []
        if payload.full_name is not None:
            changes.append(f"name: {user.full_name} → {payload.full_name}")
            user.full_name = payload.full_name
        if payload.email is not None and payload.email != user.email:
            existing = await self.user_repo.get_by_email(payload.email)
            if existing and existing.id != user_id:
                raise ValueError("A user with this email already exists.")
            changes.append(f"email: {user.email} → {payload.email}")
            user.email = payload.email

        await self.db.commit()
        await self.db.refresh(user)

        await self.audit_repo.log(
            action="update_admin",
            user_id=superadmin_id,
            resource=f"user:{user_id}",
            details=f"Updated administrator account: {', '.join(changes) if changes else 'no changes'}",
        )

        return SystemUserResponse.from_orm_user(user)

    async def promote_admin(self, user_id: str, superadmin_id: str):
        """Promote an admin to superadmin."""
        from app.schemas.user import SystemUserResponse
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.role != "admin":
            return None

        user.role = "superadmin"
        await self.db.commit()
        await self.db.refresh(user)

        await self.audit_repo.log(
            action="promote_admin",
            user_id=superadmin_id,
            resource=f"user:{user_id}",
            details=f"Promoted {user.email} from admin to superadmin",
        )

        return SystemUserResponse.from_orm_user(user)

    async def demote_admin(self, user_id: str, superadmin_id: str):
        """Demote a superadmin to admin."""
        from app.schemas.user import SystemUserResponse
        if user_id == superadmin_id:
            raise ValueError("You cannot demote your own active superadmin account.")
            
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.role != "superadmin":
            return None

        user.role = "admin"
        await self.db.commit()
        await self.db.refresh(user)

        await self.audit_repo.log(
            action="demote_admin",
            user_id=superadmin_id,
            resource=f"user:{user_id}",
            details=f"Demoted {user.email} from superadmin to admin",
        )

        return SystemUserResponse.from_orm_user(user)


    # ==========================================================
    # Support Tickets (admin)
    # ==========================================================

    async def get_all_tickets(self) -> list[SupportTicketResponse]:
        """Get all support tickets site-wide (admin view)."""
        result = await self.db.execute(
            select(SupportTicket).order_by(SupportTicket.created_at.desc())
        )
        tickets = result.scalars().all()
        from datetime import datetime
        return [
            SupportTicketResponse(
                id=t.id,
                customerId=t.customer_id,
                customerName=t.customer_name,
                category=t.category,
                description=t.description,
                status=t.status,
                adminNotes=t.admin_notes,
                customerResolutionFeedback=t.customer_resolution_feedback,
                date=t.created_at.strftime("%Y-%m-%d") if t.created_at else datetime.now().strftime("%Y-%m-%d"),
                notified=t.notified,
            )
            for t in tickets
        ]

    async def resolve_ticket(
        self,
        ticket_id: str,
        payload: ResolveTicketPayload,
        admin_id: str,
    ) -> SupportTicketResponse | None:
        """Mark a ticket as resolved with optional admin notes."""
        from datetime import datetime
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            return None

        ticket.status = "Resolved"
        if payload.admin_notes:
            ticket.admin_notes = payload.admin_notes
        ticket.notified = True
        await self.db.commit()
        await self.db.refresh(ticket)

        # Notify the customer
        from app.repositories.notification_repository import NotificationRepository
        notif_repo = NotificationRepository(self.db)
        await notif_repo.create(
            user_id=ticket.customer_id,
            text=f"Your support ticket #{ticket.id} has been resolved.",
            type="support",
            reference_id=ticket.id,
        )

        return SupportTicketResponse(
            id=ticket.id,
            customerId=ticket.customer_id,
            customerName=ticket.customer_name,
            category=ticket.category,
            description=ticket.description,
            status=ticket.status,
            adminNotes=ticket.admin_notes,
            customerResolutionFeedback=ticket.customer_resolution_feedback,
            date=ticket.created_at.strftime("%Y-%m-%d") if ticket.created_at else datetime.now().strftime("%Y-%m-%d"),
            notified=ticket.notified,
        )

    # ==========================================================
    # Offline Sales
    # ==========================================================

    def _format_sale_response(self, sale: OfflineSale) -> OfflineSaleResponse:
        from datetime import datetime
        return OfflineSaleResponse(
            id=str(sale.id),
            productName=sale.product_name,
            quantity=sale.quantity,
            totalPrice=sale.total_price,
            date=sale.created_at.strftime("%Y-%m-%d") if sale.created_at else datetime.now().strftime("%Y-%m-%d"),
            paymentMethod=sale.payment_method,
        )

    async def get_offline_sales(self) -> list[OfflineSaleResponse]:
        sales = await self.offline_sale_repo.get_all()
        return [self._format_sale_response(s) for s in sales]

    async def add_offline_sale(self, payload: OfflineSalePayload) -> OfflineSaleResponse:
        sale = await self.offline_sale_repo.create(
            product_name=payload.product_name,
            quantity=payload.quantity,
            total_price=payload.total_price,
            payment_method=payload.payment_method,
        )
        return self._format_sale_response(sale)

    async def import_offline_sales_csv(self, content: bytes) -> ImportSalesResponse:
        """Parse CSV bytes and bulk-insert offline sales."""
        try:
            text = content.decode("utf-8-sig")  # handle BOM
            reader = csv.DictReader(io.StringIO(text))
            sales_data = []
            for row in reader:
                # Normalize keys (lowercase, strip spaces)
                normalized = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()}
                sales_data.append(normalized)
        except Exception as e:
            logger.error("CSV parse error: %s", e)
            return ImportSalesResponse(imported=0, skipped=0, message="Failed to parse CSV file.")

        imported, skipped = await self.offline_sale_repo.bulk_create(sales_data)
        return ImportSalesResponse(
            imported=imported,
            skipped=skipped,
            message=f"Import complete: {imported} records imported, {skipped} skipped.",
        )

    # ==========================================================
    # CMS — Banners
    # ==========================================================

    async def create_banner(
        self,
        payload: CreateBannerRequest,
    UpdateBannerRequest,
        image_file: Optional[UploadFile] = None,
    ) -> BannerResponse:
        image_url = payload.image
        if image_file and hasattr(image_file, "filename") and image_file.filename:
            image_url = await cloudinary_service.upload_image(
                file=image_file,
                folder="chocolate-world/banners",
            )

        if not image_url:
            image_url = "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=1200&q=80"

        banner = await self.banner_repo.create(
            title=payload.title,
            subtitle=payload.subtitle,
            tag=payload.tag,
            image=image_url,
            button_text=payload.button_text,
            link=payload.link,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        return BannerResponse.from_orm_model(banner)

    async def delete_banner(self, banner_id: str, superadmin_id: str) -> bool:
        success = await self.banner_repo.delete(banner_id)
        if success:
            await self.audit_repo.log(
                action="delete_banner",
                user_id=superadmin_id,
                resource=f"banner:{banner_id}",
                details=f"Deleted banner slide: {banner_id}",
            )
        return success


    # ==========================================================
    # CMS — Testimonials
    # ==========================================================

    async def create_testimonial(
        self,
        payload: CreateTestimonialRequest,
        avatar_file: Optional[UploadFile] = None,
    ) -> TestimonialResponse:
        avatar_url = payload.avatar_url
        if avatar_file and hasattr(avatar_file, "filename") and avatar_file.filename:
            avatar_url = await cloudinary_service.upload_image(
                file=avatar_file,
                folder="chocolate-world/testimonials",
            )

        testimonial = await self.testimonial_repo.create(
            author=payload.author,
            title=payload.title,
            text=payload.text,
            rating=payload.rating,
            initials=payload.initials,
            avatar_url=avatar_url,
            is_active=payload.is_active,
            sort_order=payload.sort_order,
        )
        return TestimonialResponse.from_orm_model(testimonial)

    # ==========================================================
    # CMS — Instagram Reels
    # ==========================================================

    async def create_reel(
        self,
        payload: CreateReelRequest,
        video_file: Optional[UploadFile] = None,
    ) -> ReelResponse:
        video_url = payload.video_url
        if video_file and hasattr(video_file, "filename") and video_file.filename:
            video_url = await cloudinary_service.upload_video(
                file=video_file,
                folder="chocolate-world/reels",
            )

        if not video_url:
            video_url = "https://assets.mixkit.co/videos/preview/mixkit-chocolate-sauce-being-poured-on-dessert-42790-large.mp4"

        reel = await self.reel_repo.create(
            video_url=video_url,
            likes=payload.likes,
            comments=payload.comments,
            views=payload.views,
            title=payload.title,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        return ReelResponse(
            id=reel.id,
            videoUrl=reel.video_url,
            likes=reel.likes,
            comments=reel.comments,
            views=reel.views,
            title=reel.title,
        )

    async def delete_reel(self, reel_id: str) -> bool:
        reel = await self.reel_repo.get_by_id(reel_id)
        if not reel:
            return False
        await self.reel_repo.delete(reel_id)
        return True

    async def delete_testimonial(self, testimonial_id: str) -> bool:
        item = await self.testimonial_repo.get_by_id(testimonial_id)
        if not item:
            return False
        await self.testimonial_repo.delete(testimonial_id)
        return True


    # ==========================================================
    # CMS — Site Config (Stats / Contact)
    # ==========================================================

    async def set_stats(self, payload: SetStatsRequest) -> StatsResponse:
        await self.site_config_repo.set("stats", payload.model_dump())
        return StatsResponse(**payload.model_dump())

    async def set_contact(self, payload: SetContactRequest) -> ContactInfoResponse:
        await self.site_config_repo.set("contact", payload.model_dump())
        return ContactInfoResponse(**payload.model_dump())

    # ==========================================================
    # Contact Form Messages (Admin view & manage)
    # ==========================================================

    async def get_contact_messages(self) -> list:
        from app.repositories.contact_repository import ContactRepository
        repo = ContactRepository(self.db)
        messages = await repo.get_all()
        return [
            {
                "id": m.id,
                "name": m.name,
                "email": m.email,
                "phone": m.phone,
                "subject": m.subject,
                "message": m.message,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
            }
            for m in messages
        ]

    async def delete_contact_message(self, message_id: str) -> bool:
        from app.repositories.contact_repository import ContactRepository
        repo = ContactRepository(self.db)
        return await repo.delete(message_id)

    # ==========================================================
    # Our Story Video Upload
    # ==========================================================

    async def upload_story_video(self, video_file: UploadFile) -> str:
        """Upload crafting video for Our Story section."""
        video_url = await cloudinary_service.upload_video(
            file=video_file,
            folder="chocolate-world/story",
        )
        if not video_url:
            video_url = "https://assets.mixkit.co/videos/preview/mixkit-pouring-melted-chocolate-on-a-muffin-34289-large.mp4"
        await self.site_config_repo.set("story_video", {"video_url": video_url})
        return video_url

    async def get_story_video(self) -> str:
        data = await self.site_config_repo.get("story_video")
        if data and isinstance(data, dict) and "video_url" in data:
            return data["video_url"]
        return "https://assets.mixkit.co/videos/preview/mixkit-pouring-melted-chocolate-on-a-muffin-34289-large.mp4"

    async def delete_story_video(self) -> str:
        default_video = "https://assets.mixkit.co/videos/preview/mixkit-pouring-melted-chocolate-on-a-muffin-34289-large.mp4"
        await self.site_config_repo.set("story_video", {"video_url": default_video})
        return default_video

    # ==========================================================
    # Banner Image Upload
    # ==========================================================

    async def upload_banner_image(self, banner_id: str, image_file: UploadFile) -> str:
        """Upload banner image to Cloudinary and return its URL."""
        return await cloudinary_service.upload_image(
            file=image_file,
            folder="chocolate-world/banners",
        )


async def ensure_default_banners_exist(db: AsyncSession) -> None:
    """Seed initial luxury hero banners if banner table is empty."""
    banner_repo = BannerRepository(db)
    cnt = await banner_repo.count()
    if cnt > 0:
        return

    defaults = [
        {
            "title": "Crafted Perfection",
            "subtitle": "Discover artisanal pralines handcrafted by master chocolatiers using single-origin cacao from Ecuador.",
            "tag": "Winter Collection 2026",
            "image": "https://images.unsplash.com/photo-1548907040-4d42b52115ca?auto=format&fit=crop&w=1920&q=80",
            "button_text": "Explore Collection",
            "link": "/products",
            "sort_order": 1,
            "is_active": True,
        },
        {
            "title": "Royal Truffle Vault",
            "subtitle": "Indulge in velvety dark ganache infused with 24k edible gold dust and rare Madagascar vanilla.",
            "tag": "Signature Masterpiece",
            "image": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=1920&q=80",
            "button_text": "Order Luxury Gift",
            "link": "/products",
            "sort_order": 2,
            "is_active": True,
        },
        {
            "title": "Bespoke Gifting",
            "subtitle": "Custom personalized mahogany wooden hampers with silk velvet lining for corporate and royal celebrations.",
            "tag": "Bespoke Atelier",
            "image": "https://images.unsplash.com/photo-1582176647444-3e91129b018b?auto=format&fit=crop&w=1920&q=80",
            "button_text": "Design Your Hamper",
            "link": "/custom-hampers",
            "sort_order": 3,
            "is_active": True,
        },
    ]

    for d in defaults:
        await banner_repo.create(**d)
    logger.info("Default luxury hero banners seeded successfully.")


async def ensure_default_testimonials_exist(db: AsyncSession) -> None:
    """Ensure initial luxury testimonials exist in the database on startup."""
    testimonial_repo = TestimonialRepository(db)
    count = await testimonial_repo.count()
    if count > 0:
        return

    defaults = [
        {
            "author": "Vikram Kapoor",
            "title": "Food Critic, Mumbai",
            "text": "I've tried chocolates from Belgium, Switzerland, and France — but Chovique genuinely stands apart. The depth of flavor in their single-origin bars is extraordinary.",
            "rating": 5.0,
            "initials": "VK",
            "is_active": True,
            "sort_order": 1,
        },
        {
            "author": "Neha Patel",
            "title": "Loyal Customer, Delhi",
            "text": "Ordered a bespoke gift box for my mother's birthday. The presentation was flawless, and the chocolates were even better. Chovique turned a gift into a memory.",
            "rating": 5.0,
            "initials": "NP",
            "is_active": True,
            "sort_order": 2,
        },
        {
            "author": "Chef Ravi Joshi",
            "title": "Pastry Chef, Bangalore",
            "text": "As a pastry chef, I'm incredibly particular about chocolate. Chovique's cocoa is consistent, rich, and tempers beautifully. It's my go-to for all premium work.",
            "rating": 5.0,
            "initials": "RJ",
            "is_active": True,
            "sort_order": 3,
        },
    ]

    for d in defaults:
        await testimonial_repo.create(**d)
    logger.info("Default customer testimonials seeded successfully.")


async def ensure_default_products_exist(db: AsyncSession) -> None:
    """Ensure initial luxury chocolate products exist in the database on startup."""
    product_repo = ProductRepository(db)
    count = await product_repo.count()
    if count > 0:
        return

    defaults = [
        {
            "name": "Belgian Dark Truffle Bar",
            "slug": "belgian-dark-truffle-bar",
            "category": "dark",
            "price": 849.0,
            "original_price": 999.0,
            "weight": "100g",
            "stock": 25,
            "description": "70% Single-origin Ghanaian cocoa infused with French velvet truffle ganache and cocoa nibs.",
            "ingredients": "Ghanaian Cocoa Mass, Cocoa Butter, Organic Cane Sugar, Natural Vanilla Bean Extract.",
            "badge": "Bestseller",
            "image": "https://images.unsplash.com/photo-1548907040-4d42b52115ca?auto=format&fit=crop&w=600&q=80",
            "hover_image": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=600&q=80",
            "rating": 4.9,
            "ratings_count": 128,
            "sort_order": 1,
            "is_featured": True,
            "is_bestseller": True,
            "is_new_arrival": False,
        },
        {
            "name": "Royal Gold Truffle Box",
            "slug": "royal-gold-truffle-box",
            "category": "gift",
            "price": 2499.0,
            "original_price": 2999.0,
            "weight": "400g",
            "stock": 15,
            "description": "An opulent assortment of 16 handcrafted truffles dusted with 24K edible gold leaf in a mahogany keepsake box.",
            "ingredients": "Ecuadorian Cacao, Alpine Cream, 24K Edible Gold Dust, Hazelnut Praline.",
            "badge": "Gift Hamper",
            "image": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=600&q=80",
            "hover_image": "https://images.unsplash.com/photo-1582176647444-3e91129b018b?auto=format&fit=crop&w=600&q=80",
            "rating": 5.0,
            "ratings_count": 94,
            "sort_order": 2,
            "is_featured": True,
            "is_bestseller": True,
            "is_new_arrival": False,
        },
        {
            "name": "Salted Caramel Milk Bar",
            "slug": "salted-caramel-milk-bar",
            "category": "milk",
            "price": 699.0,
            "original_price": 799.0,
            "weight": "120g",
            "stock": 30,
            "description": "Creamy 45% Swiss milk chocolate layered with slow-cooked golden caramel and pink Himalayan sea salt.",
            "ingredients": "Whole Milk Powder, Cocoa Butter, Organic Cane Sugar, Fleur de Sel, Caramel.",
            "badge": "New",
            "image": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=600&q=80",
            "hover_image": "https://images.unsplash.com/photo-1548907040-4d42b52115ca?auto=format&fit=crop&w=600&q=80",
            "rating": 4.8,
            "ratings_count": 67,
            "sort_order": 3,
            "is_featured": False,
            "is_bestseller": False,
            "is_new_arrival": True,
        },
        {
            "name": "White Silk Berry Pralines",
            "slug": "white-silk-berry-pralines",
            "category": "white",
            "price": 899.0,
            "original_price": 1050.0,
            "weight": "150g",
            "stock": 20,
            "description": "Velvety cocoa butter white chocolate filled with freeze-dried raspberry compote and wild strawberry liquor.",
            "ingredients": "Cocoa Butter, Whole Milk Powder, Freeze-dried Raspberries, Wild Strawberry Essence.",
            "badge": "Signature",
            "image": "https://images.unsplash.com/photo-1582176647444-3e91129b018b?auto=format&fit=crop&w=600&q=80",
            "hover_image": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=600&q=80",
            "rating": 4.7,
            "ratings_count": 45,
            "sort_order": 4,
            "is_featured": True,
            "is_bestseller": False,
            "is_new_arrival": False,
        },
        {
            "name": "Ecuadorian Dark 85% Bar",
            "slug": "ecuadorian-dark-85-bar",
            "category": "dark",
            "price": 799.0,
            "original_price": 899.0,
            "weight": "100g",
            "stock": 18,
            "description": "Intense 85% single-estate dark chocolate featuring earthy floral notes and hints of toasted espresso.",
            "ingredients": "Single-estate Ecuadorian Cocoa Liquor, Cocoa Butter, Unrefined Cane Sugar.",
            "badge": "Premium",
            "image": "https://images.unsplash.com/photo-1548907040-4d42b52115ca?auto=format&fit=crop&w=600&q=80",
            "hover_image": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=600&q=80",
            "rating": 4.9,
            "ratings_count": 82,
            "sort_order": 5,
            "is_featured": True,
            "is_bestseller": False,
            "is_new_arrival": False,
        },
        {
            "name": "Artisanal Hot Cocoa Blend",
            "slug": "artisanal-hot-cocoa-blend",
            "category": "beverage",
            "price": 599.0,
            "original_price": 699.0,
            "weight": "250g",
            "stock": 40,
            "description": "Rich drinking chocolate shavings crafted from pure Venezuelan cocoa nibs and crushed bourbon vanilla bean.",
            "ingredients": "Ground Venezuelan Cocoa, Raw Cane Sugar, Ceylon Cinnamon, Madagascar Vanilla.",
            "badge": "Bestseller",
            "image": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=600&q=80",
            "hover_image": "https://images.unsplash.com/photo-1582176647444-3e91129b018b?auto=format&fit=crop&w=600&q=80",
            "rating": 4.8,
            "ratings_count": 110,
            "sort_order": 6,
            "is_featured": False,
            "is_bestseller": True,
            "is_new_arrival": False,
        },
    ]

    for d in defaults:
        await product_repo.create(**d)
    logger.info("Default luxury products seeded successfully.")
