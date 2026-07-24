import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.address_repository import AddressRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.coupon_repository import CouponRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.reel_repository import ReelRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.ticket_repository import TicketRepository
from app.repositories.user_repository import UserRepository

from app.schemas.contact import ContactMessageRequest, ContactMessageResponse
from app.schemas.coupon import CouponValidationRequest, CouponValidationResponse, UserCouponResponse
from app.schemas.order import OrderPayload, OrderResponse, CartItemResponse, ShippingAddressSchema
from app.schemas.product import ProductResponse, ReviewResponse
from app.schemas.ticket import CreateTicketPayload, SupportTicketResponse, TicketFeedbackPayload
from app.schemas.user import (
    AvatarUploadResponse,
    CustomerAddressCreate,
    CustomerAddressResponse,
    ProfileUpdatePayload,
    SupportNotificationResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)


class CustomerService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.address_repo = AddressRepository(db)
        self.coupon_repo = CouponRepository(db)
        self.order_repo = OrderRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.contact_repo = ContactRepository(db)
        self.review_repo = ReviewRepository(db)
        self.product_repo = ProductRepository(db)
        self.reel_repo = ReelRepository(db)

    # ==========================================================
    # Profile & Avatar
    # ==========================================================

    async def update_profile(
        self,
        user_id: str,
        payload: ProfileUpdatePayload,
    ) -> UserResponse:

        update_dict = {}
        if payload.full_name is not None:
            update_dict["full_name"] = payload.full_name
        elif payload.name is not None:
            update_dict["full_name"] = payload.name

        if payload.phone is not None:
            update_dict["phone"] = payload.phone
        if payload.gender is not None:
            update_dict["gender"] = payload.gender
        if payload.dob is not None:
            try:
                update_dict["dob"] = datetime.strptime(payload.dob, "%Y-%m-%d").date()
            except Exception:
                pass

        if payload.address_street is not None:
            update_dict["address_street"] = payload.address_street
        if payload.address_city is not None:
            update_dict["address_city"] = payload.address_city
        if payload.address_state is not None:
            update_dict["address_state"] = payload.address_state
        if payload.address_zip is not None:
            update_dict["address_zip"] = payload.address_zip

        user = await self.user_repo.update_profile(user_id, **update_dict)
        return UserResponse.model_validate(user)

    async def upload_avatar(
        self,
        user_id: str,
        file: UploadFile,
    ) -> AvatarUploadResponse:

        os.makedirs("static/avatars", exist_ok=True)
        ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join("static/avatars", filename)

        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        avatar_url = f"/static/avatars/{filename}"
        await self.user_repo.update_profile(user_id, avatar_url=avatar_url)

        return AvatarUploadResponse(avatar_url=avatar_url)

    # ==========================================================
    # Addresses
    # ==========================================================

    async def get_addresses(self, user_id: str) -> list[CustomerAddressResponse]:
        addresses = await self.address_repo.get_user_addresses(user_id)
        return [
            CustomerAddressResponse(
                id=a.id,
                title=a.title,
                name=a.name,
                street=a.street,
                city=a.city,
                state=a.state,
                zip=a.zip,
                phone=a.phone,
                isDefault=a.is_default,
            )
            for a in addresses
        ]

    async def add_address(
        self,
        user_id: str,
        payload: CustomerAddressCreate,
    ) -> CustomerAddressResponse:

        addr = await self.address_repo.create(
            user_id=user_id,
            title=payload.title,
            name=payload.name,
            street=payload.street,
            city=payload.city,
            state=payload.state,
            zip=payload.zip,
            phone=payload.phone,
            is_default=payload.isDefault,
        )

        return CustomerAddressResponse(
            id=addr.id,
            title=addr.title,
            name=addr.name,
            street=addr.street,
            city=addr.city,
            state=addr.state,
            zip=addr.zip,
            phone=addr.phone,
            isDefault=addr.is_default,
        )

    async def delete_address(self, user_id: str, address_id: str) -> bool:
        return await self.address_repo.delete(address_id, user_id)

    async def set_default_address(
        self,
        user_id: str,
        address_id: str,
    ) -> CustomerAddressResponse | None:

        addr = await self.address_repo.set_default(address_id, user_id)
        if not addr:
            return None

        return CustomerAddressResponse(
            id=addr.id,
            title=addr.title,
            name=addr.name,
            street=addr.street,
            city=addr.city,
            state=addr.state,
            zip=addr.zip,
            phone=addr.phone,
            isDefault=addr.is_default,
        )

    # ==========================================================
    # Coupons
    # ==========================================================

    async def validate_coupon(
        self,
        code: str,
    ) -> CouponValidationResponse:

        coupon = await self.coupon_repo.get_by_code(code)
        if not coupon:
            return CouponValidationResponse(
                valid=False,
                code=code,
                discount_percent=0.0,
                discount_amount=0.0,
                message="Invalid or expired promo code.",
            )

        return CouponValidationResponse(
            valid=True,
            code=coupon.code,
            discount_percent=coupon.discount_percent,
            discount_amount=coupon.discount_amount if coupon.discount_amount > 0 else None,
            message=f"Promo code {coupon.code} applied successfully!",
        )

    async def get_user_coupons(self, user_id: str) -> list[UserCouponResponse]:
        coupons = await self.coupon_repo.get_active_coupons()
        return [
            UserCouponResponse(
                code=c.code,
                desc=c.description,
                exp=c.expires_at.strftime("%Y-%m-%d") if c.expires_at else "2026-12-31",
                discountPercent=c.discount_percent,
            )
            for c in coupons
        ]

    # ==========================================================
    # Orders
    # ==========================================================

    async def place_order(
        self,
        user_id: str,
        payload: OrderPayload,
    ) -> OrderResponse:

        subtotal = 0.0
        items_data = []

        for item in payload.items:
            product = await self.product_repo.get_by_id(item.product_id)
            if not product:
                raise ValueError(f"Product with ID {item.product_id} not found.")

            item_price = product.price
            subtotal += item_price * item.quantity
            items_data.append({
                "product_id": product.id,
                "quantity": item.quantity,
                "price": item_price,
            })

        discount = 0.0
        if payload.coupon_code:
            coupon = await self.coupon_repo.get_by_code(payload.coupon_code)
            if coupon:
                if coupon.discount_percent > 0:
                    discount = (subtotal * coupon.discount_percent) / 100.0
                elif coupon.discount_amount > 0:
                    discount = coupon.discount_amount

        shipping = 0.0 if subtotal > 1500 else 99.0
        total = max(0.0, subtotal - discount + shipping)

        shipping_addr_dict = payload.shipping_address.model_dump()

        order = await self.order_repo.create_order(
            user_id=user_id,
            total=round(total, 2),
            subtotal=round(subtotal, 2),
            discount=round(discount, 2),
            shipping=round(shipping, 2),
            shipping_address=shipping_addr_dict,
            delivery_option=payload.delivery_option,
            payment_method=payload.payment_method,
            items_data=items_data,
        )

        return self._format_order_response(order)

    async def get_user_orders(self, user_id: str) -> list[OrderResponse]:
        orders = await self.order_repo.get_user_orders(user_id)
        return [self._format_order_response(o) for o in orders]

    async def get_order_by_id(self, order_id: str, user_id: str) -> OrderResponse | None:
        order = await self.order_repo.get_by_id(order_id)
        if not order or order.user_id != user_id:
            return None
        return self._format_order_response(order)

    def _format_order_response(self, order) -> OrderResponse:
        cart_items = []
        for item in order.items:
            product_res = ProductResponse.from_orm_model(item.product)
            cart_items.append(CartItemResponse(product=product_res, quantity=item.quantity))

        ship_addr = ShippingAddressSchema(**order.shipping_address)

        created_date = order.created_at.strftime("%Y-%m-%d") if order.created_at else datetime.now().strftime("%Y-%m-%d")

        return OrderResponse(
            id=order.id,
            items=cart_items,
            total=order.total,
            subtotal=order.subtotal,
            discount=order.discount,
            shipping=order.shipping,
            date=created_date,
            status=order.status,
            shippingAddress=ship_addr,
            deliveryOption=order.delivery_option,
            paymentMethod=order.payment_method,
        )

    # ==========================================================
    # Support Tickets
    # ==========================================================

    async def get_user_tickets(self, user_id: str) -> list[SupportTicketResponse]:
        tickets = await self.ticket_repo.get_user_tickets(user_id)
        return [self._format_ticket_response(t) for t in tickets]

    async def get_ticket_by_id(self, ticket_id: str, user_id: str) -> SupportTicketResponse | None:
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket or ticket.customer_id != user_id:
            return None
        return self._format_ticket_response(ticket)

    async def create_ticket(
        self,
        user: User,
        payload: CreateTicketPayload,
    ) -> SupportTicketResponse:

        ticket = await self.ticket_repo.create(
            customer_id=user.id,
            customer_name=user.full_name,
            category=payload.category,
            description=payload.description,
            status="Pending",
        )

        # Create confirmation notification for customer
        await self.notification_repo.create(
            user_id=user.id,
            text=f"Support ticket #{ticket.id} received. Our team will update you shortly.",
            type="support",
            reference_id=ticket.id,
        )

        return self._format_ticket_response(ticket)

    async def submit_ticket_feedback(
        self,
        ticket_id: str,
        user_id: str,
        payload: TicketFeedbackPayload,
    ) -> SupportTicketResponse | None:

        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket or ticket.customer_id != user_id:
            return None

        updated = await self.ticket_repo.update_feedback(ticket_id, payload.feedback)
        return self._format_ticket_response(updated)

    def _format_ticket_response(self, ticket) -> SupportTicketResponse:
        created_date = ticket.created_at.strftime("%Y-%m-%d") if ticket.created_at else datetime.now().strftime("%Y-%m-%d")

        return SupportTicketResponse(
            id=ticket.id,
            customerId=ticket.customer_id,
            customerName=ticket.customer_name,
            category=ticket.category,
            description=ticket.description,
            status=ticket.status,
            adminNotes=ticket.admin_notes,
            customerResolutionFeedback=ticket.customer_resolution_feedback,
            date=created_date,
            notified=ticket.notified,
        )

    # ==========================================================
    # Notifications
    # ==========================================================

    async def get_user_notifications(self, user_id: str) -> list[SupportNotificationResponse]:
        notifs = await self.notification_repo.get_user_notifications(user_id)
        return [
            SupportNotificationResponse(
                id=n.id,
                text=n.text,
                date=n.created_at.strftime("%Y-%m-%d") if n.created_at else datetime.now().strftime("%Y-%m-%d"),
                read=n.read,
                type=n.type,
                referenceId=n.reference_id,
            )
            for n in notifs
        ]

    async def mark_notification_read(self, user_id: str, notification_id: str) -> SupportNotificationResponse | None:
        notif = await self.notification_repo.mark_read(notification_id, user_id)
        if not notif:
            return None

        return SupportNotificationResponse(
            id=notif.id,
            text=notif.text,
            date=notif.created_at.strftime("%Y-%m-%d") if notif.created_at else datetime.now().strftime("%Y-%m-%d"),
            read=notif.read,
            type=notif.type,
            referenceId=notif.reference_id,
        )

    async def delete_notification(self, user_id: str, notification_id: str) -> bool:
        return await self.notification_repo.delete(notification_id, user_id)

    # ==========================================================
    # Contact Form
    # ==========================================================

    async def submit_contact(
        self,
        payload: ContactMessageRequest,
    ) -> ContactMessageResponse:

        name = payload.name
        if not name:
            fname = payload.first_name or ""
            lname = payload.last_name or ""
            name = f"{fname} {lname}".strip() or "Anonymous"

        await self.contact_repo.create(
            name=name,
            email=payload.email,
            phone=payload.phone,
            subject=payload.subject,
            message=payload.message,
        )

        return ContactMessageResponse(
            message="Thanks — we'll get back to you within 24 hours."
        )

    # ==========================================================
    # Product Reviews
    # ==========================================================

    async def get_product_reviews(self, product_id: str) -> list[ReviewResponse]:
        reviews = await self.review_repo.get_product_reviews(product_id)
        return [
            ReviewResponse(
                id=r.id,
                author=r.author,
                rating=r.rating,
                text=r.text,
                date=r.created_at.strftime("%Y-%m-%d") if r.created_at else datetime.now().strftime("%Y-%m-%d"),
                avatar=r.avatar,
            )
            for r in reviews
        ]

    async def create_product_review(
        self,
        product_id: str,
        author: str,
        rating: float,
        text: str,
        user_id: str | None = None,
    ) -> ReviewResponse:

        initials = "".join([w[0].upper() for w in author.split()[:2]]) if author else "U"

        review = await self.review_repo.create(
            product_id=product_id,
            user_id=user_id,
            author=author,
            rating=rating,
            text=text,
            avatar=initials,
        )

        return ReviewResponse(
            id=review.id,
            author=review.author,
            rating=review.rating,
            text=review.text,
            date=review.created_at.strftime("%Y-%m-%d"),
            avatar=review.avatar,
        )
