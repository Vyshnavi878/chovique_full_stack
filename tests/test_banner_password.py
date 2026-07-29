"""
Tests for Admin Banner Management and Password Updates.
"""

import pytest
from httpx import AsyncClient
from app.db.seed_data import seed_database
from app.core.security import create_access_token
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.asyncio


async def _seed_and_get_superadmin_headers():
    async with TestSessionLocal() as session:
        await seed_database(session)
    token = create_access_token(data={"sub": "superadmin-001", "role": "superadmin"})
    return {"Authorization": f"Bearer {token}"}


class TestBannerAndPasswordManagement:

    async def test_banner_lifecycle(self, client: AsyncClient):
        headers = await _seed_and_get_superadmin_headers()

        # 1. Create a banner
        create_res = await client.post(
            "/api/v1/admin/banners",
            headers=headers,
            data={
                "title": "Test Gold Truffles",
                "subtitle": "Limited luxury edition",
                "tag": "Exclusive",
                "button_text": "Buy Now",
                "link": "/products",
            },
        )
        assert create_res.status_code == 201
        banner_data = create_res.json()
        assert banner_data["title"] == "Test Gold Truffles"
        banner_id = banner_data["id"]

        # 2. Get active banners
        get_res = await client.get("/api/v1/home/banners")
        assert get_res.status_code == 200
        titles = [b["title"] for b in get_res.json()]
        assert "Test Gold Truffles" in titles

        # 3. Delete banner
        del_res = await client.delete(
            f"/api/v1/admin/banners/{banner_id}",
            headers=headers,
        )
        assert del_res.status_code == 204

    async def test_admin_password_update(self, client: AsyncClient):
        headers = await _seed_and_get_superadmin_headers()

        # 1. Create admin user
        admin_res = await client.post(
            "/api/v1/admin/users",
            headers=headers,
            json={
                "full_name": "Test Admin",
                "email": "testadmin@chovique.com",
                "password": "InitialPass123",
                "scope": "All Boutiques",
            },
        )
        assert admin_res.status_code == 201
        admin_id = admin_res.json()["id"]

        # 2. Update password for admin
        pw_res = await client.patch(
            f"/api/v1/admin/users/{admin_id}/password",
            headers=headers,
            json={"password": "NewSecretPassword123!"},
        )
        assert pw_res.status_code == 200
        assert pw_res.json()["message"] == "Administrator password updated successfully."

        # 3. Test login with new password
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testadmin@chovique.com",
                "password": "NewSecretPassword123!",
            },
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["role"] == "admin"
