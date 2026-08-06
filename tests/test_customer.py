"""
Customer API tests.

Covers: profile update, avatar upload, address book, coupon validation,
order placement & list, support tickets, notifications, contact form, product reviews.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

from app.db.seed_data import seed_database
from app.models.coupon import Coupon
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.asyncio


async def _seed():
    async with TestSessionLocal() as session:
        await seed_database(session)


# ==========================================================
# Profile & Address Tests
# ==========================================================

class TestCustomerProfileAndAddress:

    async def test_update_profile(self, authenticated_client: AsyncClient):
        response = await authenticated_client.patch(
            "/api/v1/users/me",
            json={
                "phone": "+91 99999 88888",
                "gender": "male",
                "address_city": "Mumbai",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["phone"] == "+91 99999 88888"
        assert data["profile"]["gender"] == "male"
        assert data["profile"]["address"]["city"] == "Mumbai"

    async def test_add_and_list_address(self, authenticated_client: AsyncClient):
        # Add address
        res = await authenticated_client.post(
            "/api/v1/users/me/addresses",
            json={
                "title": "Home",
                "name": "Test User",
                "street": "123 Chocolate Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "zip": "400001",
                "phone": "+91 98765 43210",
                "isDefault": True,
            },
        )
        assert res.status_code == 201
        addr = res.json()
        assert addr["title"] == "Home"
        assert addr["isDefault"] is True

        # Get list
        res_list = await authenticated_client.get("/api/v1/users/me/addresses")
        assert res_list.status_code == 200
        addresses = res_list.json()
        assert len(addresses) == 1
        assert addresses[0]["id"] == addr["id"]

    async def test_set_default_and_delete_address(self, authenticated_client: AsyncClient):
        # Create address 1
        res1 = await authenticated_client.post(
            "/api/v1/users/me/addresses",
            json={
                "title": "Home",
                "name": "Test User",
                "street": "123 Street",
                "city": "Mumbai",
                "state": "MH",
                "zip": "400001",
                "phone": "9876543210",
                "isDefault": True,
            },
        )
        addr1_id = res1.json()["id"]

        # Create address 2
        res2 = await authenticated_client.post(
            "/api/v1/users/me/addresses",
            json={
                "title": "Office",
                "name": "Test User",
                "street": "456 Office Rd",
                "city": "Mumbai",
                "state": "MH",
                "zip": "400002",
                "phone": "9876543210",
                "isDefault": False,
            },
        )
        addr2_id = res2.json()["id"]

        # Set address 2 as default
        def_res = await authenticated_client.patch(
            f"/api/v1/users/me/addresses/{addr2_id}/default"
        )
        assert def_res.status_code == 200
        assert def_res.json()["isDefault"] is True

        # Delete address 1
        del_res = await authenticated_client.delete(
            f"/api/v1/users/me/addresses/{addr1_id}"
        )
        assert del_res.status_code == 204


# ==========================================================
# Coupon Tests
# ==========================================================

class TestCoupons:

    async def test_validate_coupon_success(self, client: AsyncClient):
        await _seed()
        res = await client.post(
            "/api/v1/coupons/validate",
            json={"code": "CHOVIQUE10"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["discount_percent"] == 10.0

    async def test_validate_coupon_invalid(self, client: AsyncClient):
        await _seed()
        res = await client.post(
            "/api/v1/coupons/validate",
            json={"code": "INVALIDCODE"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False

    async def test_validate_expired_coupon(self, client: AsyncClient):
        """An expired coupon must be rejected by /coupons/validate."""
        async with TestSessionLocal() as session:
            expired_coupon = Coupon(
                code="EXPIRED10",
                description="Expired test coupon",
                discount_percent=10.0,
                discount_amount=0.0,
                is_active=True,
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
            session.add(expired_coupon)
            await session.commit()

        res = await client.post(
            "/api/v1/coupons/validate",
            json={"code": "EXPIRED10"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert data["message"] == "Invalid or expired promo code."

    async def test_validate_inactive_coupon(self, client: AsyncClient):
        """An is_active=False coupon must be rejected by /coupons/validate."""
        async with TestSessionLocal() as session:
            inactive_coupon = Coupon(
                code="INACTIVE10",
                description="Inactive test coupon",
                discount_percent=10.0,
                discount_amount=0.0,
                is_active=False,
                expires_at=None,
            )
            session.add(inactive_coupon)
            await session.commit()

        res = await client.post(
            "/api/v1/coupons/validate",
            json={"code": "INACTIVE10"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert data["message"] == "Invalid or expired promo code."

    async def test_user_coupons_list(self, authenticated_client: AsyncClient):
        await _seed()
        res = await authenticated_client.get("/api/v1/users/me/coupons")
        assert res.status_code == 200
        coupons = res.json()
        assert len(coupons) > 0


# ==========================================================
# Orders Tests
# ==========================================================

class TestOrders:

    async def test_place_and_get_order(self, authenticated_client: AsyncClient):
        await _seed()

        order_payload = {
            "items": [{"product_id": "p1", "quantity": 2}],
            "shipping_address": {
                "name": "Test User",
                "street": "123 Main St",
                "city": "Mumbai",
                "state": "Maharashtra",
                "zip": "400001",
                "phone": "+91 98765 43210",
            },
            "delivery_option": "Express Delivery",
            "payment_method": "UPI",
            "coupon_code": "CHOVIQUE10",
        }

        res = await authenticated_client.post("/api/v1/orders", json=order_payload)
        assert res.status_code == 201
        order = res.json()
        assert order["id"].startswith("ORD-")
        assert len(order["items"]) == 1
        assert order["subtotal"] == 1698.0
        assert order["discount"] == 169.8
        assert order["status"] == "Processing"

        # Fetch user orders
        orders_res = await authenticated_client.get("/api/v1/orders")
        assert orders_res.status_code == 200
        orders = orders_res.json()
        assert len(orders) == 1
        assert orders[0]["id"] == order["id"]

        # Fetch single order
        single_res = await authenticated_client.get(f"/api/v1/orders/{order['id']}")
        assert single_res.status_code == 200
        assert single_res.json()["id"] == order["id"]


# ==========================================================
# Support Tickets & Notifications Tests
# ==========================================================

class TestSupportAndNotifications:

    async def test_create_and_feedback_ticket(self, authenticated_client: AsyncClient):
        res = await authenticated_client.post(
            "/api/v1/support/tickets",
            json={
                "category": "Chocolate melted",
                "description": "My chocolate melted during delivery.",
            },
        )
        assert res.status_code == 201
        ticket = res.json()
        assert ticket["id"].startswith("TKT-")
        assert ticket["category"] == "Chocolate melted"
        assert ticket["status"] == "Pending"

        # List tickets
        list_res = await authenticated_client.get("/api/v1/support/tickets")
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        # Submit feedback
        fb_res = await authenticated_client.post(
            f"/api/v1/support/tickets/{ticket['id']}/feedback",
            json={"feedback": "Resolved"},
        )
        assert fb_res.status_code == 200
        assert fb_res.json()["customerResolutionFeedback"] == "Resolved"

    async def test_notifications(self, authenticated_client: AsyncClient):
        # Create ticket triggers a notification
        await authenticated_client.post(
            "/api/v1/support/tickets",
            json={
                "category": "Other",
                "description": "General question.",
            },
        )

        res = await authenticated_client.get("/api/v1/users/me/notifications")
        assert res.status_code == 200
        notifs = res.json()
        assert len(notifs) >= 1
        notif_id = notifs[0]["id"]

        # Mark read
        read_res = await authenticated_client.patch(
            f"/api/v1/users/me/notifications/{notif_id}/read"
        )
        assert read_res.status_code == 200
        assert read_res.json()["read"] is True

        # Delete notification
        del_res = await authenticated_client.delete(
            f"/api/v1/users/me/notifications/{notif_id}"
        )
        assert del_res.status_code == 204


# ==========================================================
# Contact Form Tests
# ==========================================================

class TestContactForm:

    async def test_submit_contact(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/contact",
            json={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "+91 99999 00000",
                "subject": "Corporate Order Query",
                "message": "Interested in bulk hampers for festive season.",
            },
        )
        assert res.status_code == 201
        assert "Thanks" in res.json()["message"]


# ==========================================================
# Product Review Tests
# ==========================================================

class TestProductReviews:

    async def test_add_and_get_reviews(self, client: AsyncClient):
        await _seed()

        # Add review
        res = await client.post(
            "/api/v1/products/p1/reviews",
            json={
                "author": "Chef Ravi",
                "rating": 5.0,
                "text": "Best dark chocolate bar in the market!",
            },
        )
        assert res.status_code == 201
        rev = res.json()
        assert rev["author"] == "Chef Ravi"
        assert rev["rating"] == 5.0

        # Get product reviews
        get_res = await client.get("/api/v1/products/p1/reviews")
        assert get_res.status_code == 200
        reviews = get_res.json()
        assert len(reviews) == 1
        assert reviews[0]["author"] == "Chef Ravi"
