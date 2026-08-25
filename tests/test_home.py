"""
Home page endpoint tests.

Covers: aggregated home data, banners, testimonials, stats, contact.
Tests empty database graceful handling.
"""

import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio


# ==========================================================
# Home Page — Empty Database
# ==========================================================

class TestHomePageEmpty:

    async def test_home_page_empty_db(self, client: AsyncClient):
        """Home page should return gracefully with empty lists."""
        response = await client.get("/api/v1/home")
        assert response.status_code == 200
        data = response.json()
        assert data["banners"] == []
        assert data["featured_products"] == []
        assert data["bestsellers"] == []
        assert data["new_arrivals"] == []
        assert data["testimonials"] == []
        # Stats should have defaults
        assert data["stats"]["happy_customers"] == 50000

    async def test_banners_empty_db(self, client: AsyncClient):
        response = await client.get("/api/v1/home/banners")
        assert response.status_code == 200
        assert response.json() == []

    async def test_testimonials_empty_db(self, client: AsyncClient):
        response = await client.get("/api/v1/home/testimonials")
        assert response.status_code == 200
        assert response.json() == []

    async def test_stats_empty_db(self, client: AsyncClient):
        response = await client.get("/api/v1/home/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["happy_customers"] == 50000

    async def test_contact_empty_db(self, client: AsyncClient):
        response = await client.get("/api/v1/home/contact")
        assert response.status_code == 200

