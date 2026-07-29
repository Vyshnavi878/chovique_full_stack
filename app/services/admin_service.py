import csv
import io
import logging
import os
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.resend import resend_email
from app.models.offline_sale import OfflineSale
from app.models.order import Order
from app.models.product import Product
from app.models.ticket import SupportTicket
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.offline_sale_repository import OfflineSaleRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.ticket_repository import TicketRepository
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password
from app.schemas.admin import (
    CreateAdminRequest,
    DashboardStatsResponse,
    ImportSalesResponse,
    OfflineSalePayload,
    OfflineSaleResponse,
    ResolveTicketPayload,
    UpdateOrderStatusPayload,
)
from app.schemas.order import OrderResponse
from app.schemas.ticket import SupportTicketResponse
from app.schemas.user import SystemUserResponse, UserResponse

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

    # ==========================================================
    # Dashboard Stats
    # ==========================================================

    async def get_dashboard_stats(self) -> DashboardStatsResponse:
        sales_result = await self.db.execute(select(func.sum(Order.total)))
        total_sales = sales_result.scalar() or 0.0

        orders_result = await self.db.execute(select(func.count()).select_from(Order))
        total_orders = orders_result.scalar() or 0

        users_result = await self.db.execute(select(func.count()).select_from(User))
        total_customers = users_result.scalar() or 0

        products_result = await self.db.execute(select(func.count()).select_from(Product))
        total_products = products_result.scalar() or 0

        low_stock_result = await self.db.execute(
            select(func.count()).select_from(Product).where(Product.stock <= 10)
        )
        low_stock_products_count = low_stock_result.scalar() or 0

        tickets_result = await self.db.execute(
            select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "Pending")
        )
        pending_tickets_count = tickets_result.scalar() or 0

        return DashboardStatsResponse(
            total_sales=round(total_sales, 2),
            total_orders=total_orders,
            total_customers=total_customers,
            total_products=total_products,
            low_stock_products_count=low_stock_products_count,
            pending_tickets_count=pending_tickets_count,
        )

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

    async def create_admin(self, payload: CreateAdminRequest, superadmin_id: str) -> SystemUserResponse:
        existing = await self.user_repo.get_by_email(payload.email)
        if existing:
            raise ValueError("User with this email already exists.")

        hashed_pw = hash_password(payload.password)
        new_admin = await self.user_repo.create(
            email=payload.email,
            hashed_password=hashed_pw,
            full_name=payload.full_name,
            role="admin",
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
    # Banner Image Upload
    # ==========================================================

    async def upload_banner_image(self, banner_id: str, file_content: bytes, filename: str) -> str:
        """Upload banner image to Cloudinary or save locally and return its URL."""
        from app.integrations.cloudinary import cloudinary_service
        return await cloudinary_service.upload_image(
            file_bytes=file_content,
            filename=filename,
            folder="banners",
        )

