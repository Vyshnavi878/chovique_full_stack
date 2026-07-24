"""
Home page endpoint tests.

Covers: aggregated home data, banners, testimonials, stats, contact.
Tests empty database graceful handling and seeded data.
"""

import pytest
from httpx import AsyncClient

from app.db.seed_data import seed_database
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.asyncio


# ==========================================================
# Helper: Seed test data
# ==========================================================

async def _seed():
    """Seed the test database with sample data."""
    async with TestSessionLocal() as session:
        await seed_database(session)


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


# ==========================================================
# Home Page — With Seed Data
# ==========================================================

class TestHomePageSeeded:

    async def test_home_page_with_data(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/home")
        assert response.status_code == 200
        data = response.json()

        # Banners
        assert len(data["banners"]) == 4
        assert data["banners"][0]["title"] == "The Art of Fine Chocolate"

        # Featured products
        assert len(data["featured_products"]) > 0

        # Bestsellers (badge = Bestseller or Premium)
        assert len(data["bestsellers"]) > 0

        # New arrivals (badge = New or Limited)
        assert len(data["new_arrivals"]) > 0

        # Testimonials
        assert len(data["testimonials"]) == 3

        # Stats
        assert data["stats"]["happy_customers"] == 50000
        assert data["stats"]["unique_flavors"] == 120

        # Contact
        assert data["contact"]["email"] == "hello@chovique.com"

    async def test_banners_with_data(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/home/banners")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        # Check camelCase field names (frontend compat)
        assert "buttonText" in data[0]

    async def test_testimonials_with_data(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/home/testimonials")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["author"] == "Vikram Kapoor"
