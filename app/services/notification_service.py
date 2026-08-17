import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)

logger = logging.getLogger(__name__)


class NotificationService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    def _map_notification(self, n) -> NotificationResponse:
        title = n.title or (n.type.replace('_', ' ').title() if n.type else "Notification")
        message = n.message or n.text or ""
        is_read = bool(getattr(n, "is_read", False) or getattr(n, "read", False))
        return NotificationResponse(
            id=n.id,
            admin_id=n.admin_id,
            type=n.type or "general",
            title=title,
            message=message,
            related_entity_type=n.related_entity_type,
            related_entity_id=n.related_entity_id or getattr(n, "reference_id", None),
            is_read=is_read,
            created_at=n.created_at,
        )

    async def get_admin_notifications(
        self,
        admin_id: str,
        type_filter: Optional[str] = None,
        is_read_filter: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
    ) -> NotificationListResponse:
        items, total = await self.repo.get_admin_notifications(
            admin_id=admin_id,
            type_filter=type_filter,
            is_read_filter=is_read_filter,
            page=page,
            limit=limit,
        )
        unread_count = await self.repo.get_admin_unread_count(admin_id)

        responses = [self._map_notification(n) for n in items]
        return NotificationListResponse(
            items=responses,
            total=total,
            page=page,
            limit=limit,
            unread_count=unread_count,
        )

    async def get_unread_count(self, admin_id: str) -> UnreadCountResponse:
        cnt = await self.repo.get_admin_unread_count(admin_id)
        return UnreadCountResponse(unread_count=cnt)

    async def mark_as_read(self, notification_id: str, admin_id: str) -> Optional[NotificationResponse]:
        notif = await self.repo.mark_admin_read(notification_id, admin_id)
        if not notif:
            return None
        return self._map_notification(notif)

    async def mark_all_as_read(self, admin_id: str) -> int:
        return await self.repo.mark_admin_read_all(admin_id)

    # ======================================================
    # EVENT TRIGGER HELPERS
    # ======================================================

    async def notify_new_order(self, order_id: str, order_number: str, total_amount: float, commit: bool = True):
        """Notification type: new_order"""
        try:
            title = "New Order Received"
            message = f"Order #{order_number} for ₹{total_amount:,.2f} has been placed."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="new_order",
                title=title,
                message=message,
                related_entity_type="order",
                related_entity_id=order_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create new_order notification: %s", e)

    async def notify_low_stock(self, product_id: str, product_name: str, stock: int, commit: bool = True):
        """Notification type: low_stock"""
        try:
            title = "Low Stock Alert"
            message = f"{product_name} is running low ({stock} remaining)."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="low_stock",
                title=title,
                message=message,
                related_entity_type="product",
                related_entity_id=product_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create low_stock notification: %s", e)

    async def notify_new_customer(self, user_id: str, full_name: str, commit: bool = True):
        """Notification type: new_customer"""
        try:
            title = "New Customer Registered"
            message = f"{full_name or 'A new customer'} has joined CHOVIQUE."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="new_customer",
                title=title,
                message=message,
                related_entity_type="customer",
                related_entity_id=user_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create new_customer notification: %s", e)

    async def notify_payment_failure(self, order_id: str, order_number: str, reason: str = "", commit: bool = True):
        """Notification type: payment_failure"""
        try:
            title = "Payment Failed"
            message = f"Payment failed for Order #{order_number}."
            if reason:
                message += f" ({reason})"
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="payment_failure",
                title=title,
                message=message,
                related_entity_type="order",
                related_entity_id=order_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create payment_failure notification: %s", e)

    async def notify_coupon_usage(self, coupon_code: str, order_id: str, user_name: str = "Customer", commit: bool = True):
        """Notification type: coupon_usage"""
        try:
            title = "Coupon Used"
            message = f"Coupon {coupon_code} used by {user_name}."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="coupon_usage",
                title=title,
                message=message,
                related_entity_type="coupon",
                related_entity_id=coupon_code,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create coupon_usage notification: %s", e)

    async def notify_support_message(self, ticket_id: str, user_name: str, subject: str, commit: bool = True):
        """Notification type: support_message"""
        try:
            title = "Customer Support Message"
            message = f"{user_name}: {subject}"
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="support_message",
                title=title,
                message=message,
                related_entity_type="ticket",
                related_entity_id=ticket_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create support_message notification: %s", e)

    async def notify_payment_success(self, order_id: str, order_number: str, amount: float, commit: bool = True):
        """Notification type: payment_success"""
        try:
            title = "Payment Successful"
            message = f"Payment of ₹{amount:,.2f} received for Order #{order_number}."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="payment_success",
                title=title,
                message=message,
                related_entity_type="order",
                related_entity_id=order_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create payment_success notification: %s", e)

    async def notify_order_cancelled(self, order_id: str, order_number: str, reason: str = "", commit: bool = True):
        """Notification type: order_cancelled"""
        try:
            title = "Order Cancelled"
            message = f"Order #{order_number} has been cancelled."
            if reason:
                message += f" ({reason})"
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="order_cancelled",
                title=title,
                message=message,
                related_entity_type="order",
                related_entity_id=order_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create order_cancelled notification: %s", e)

    async def notify_refund_initiated(self, order_id: str, amount: float, commit: bool = True):
        """Notification type: refund_initiated"""
        try:
            title = "Refund Initiated"
            message = f"Refund of ₹{amount:,.2f} initiated for Order #{order_id}."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="refund_initiated",
                title=title,
                message=message,
                related_entity_type="order",
                related_entity_id=order_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create refund_initiated notification: %s", e)

    async def notify_refund_completed(self, order_id: str, amount: float, commit: bool = True):
        """Notification type: refund_completed"""
        try:
            title = "Refund Completed"
            message = f"Refund of ₹{amount:,.2f} completed for Order #{order_id}."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="refund_completed",
                title=title,
                message=message,
                related_entity_type="order",
                related_entity_id=order_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create refund_completed notification: %s", e)

    async def notify_out_of_stock(self, product_id: str, product_name: str, commit: bool = True):
        """Notification type: out_of_stock"""
        try:
            title = "Out of Stock Alert"
            message = f"{product_name} is currently out of stock!"
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="out_of_stock",
                title=title,
                message=message,
                related_entity_type="product",
                related_entity_id=product_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create out_of_stock notification: %s", e)

    async def notify_new_offline_sale(self, receipt_number: str, total_amount: float, commit: bool = True):
        """Notification type: offline_sale"""
        try:
            title = "New Offline Sale Registered"
            message = f"Receipt #{receipt_number} for ₹{total_amount:,.2f} recorded."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="offline_sale",
                title=title,
                message=message,
                related_entity_type="offline_sale",
                related_entity_id=receipt_number,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create offline_sale notification: %s", e)

    async def notify_offline_sale_update(self, receipt_number: str, action: str = "updated", commit: bool = True):
        """Notification type: offline_sale_update"""
        try:
            title = f"Offline Sale {action.capitalize()}"
            message = f"Offline receipt #{receipt_number} was {action}."
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="offline_sale_update",
                title=title,
                message=message,
                related_entity_type="offline_sale",
                related_entity_id=receipt_number,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create offline_sale_update notification: %s", e)

    async def notify_product_alert(self, product_id: str, title: str, message: str, commit: bool = True):
        """Notification type: product_alert"""
        try:
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="product_alert",
                title=title,
                message=message,
                related_entity_type="product",
                related_entity_id=product_id,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create product_alert notification: %s", e)

    async def notify_coupon_alert(self, coupon_code: str, title: str, message: str, commit: bool = True):
        """Notification type: coupon_alert"""
        try:
            await self.repo.create_admin_notification_if_not_exists(
                admin_id=None,
                type="coupon_alert",
                title=title,
                message=message,
                related_entity_type="coupon",
                related_entity_id=coupon_code,
                commit=commit
            )
        except Exception as e:
            logger.error("Failed to create coupon_alert notification: %s", e)


