"""
Product endpoint tests.

Covers: listing, filtering, search, pagination, single product,
and admin CRUD operations.
"""

import pytest
from httpx import AsyncClient

from app.db.seed_data import seed_database
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.asyncio


# ==========================================================
# Helper
# ==========================================================

async def _seed():
    async with TestSessionLocal() as session:
        await seed_database(session)


# ==========================================================
# Product Listing
# ==========================================================

class TestProductList:

    async def test_products_empty_db(self, client: AsyncClient):
        response = await client.get("/api/v1/products")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_products_with_data(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 8
        assert len(data["items"]) == 8
        assert data["page"] == 1

    async def test_products_pagination(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products?page=1&per_page=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 8
        assert data["total_pages"] == 3

    async def test_products_filter_by_category(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products?category=dark")
        assert response.status_code == 200
        data = response.json()
        assert all(p["category"] == "dark" for p in data["items"])

    async def test_products_search(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products?search=truffle")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert any("Truffle" in p["name"] for p in data["items"])

    async def test_products_sort_by_price(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products?sort=price_asc")
        assert response.status_code == 200
        data = response.json()
        prices = [p["price"] for p in data["items"]]
        assert prices == sorted(prices)

    async def test_products_filter_by_price_range(self, client: AsyncClient):
        await _seed()

        response = await client.get(
            "/api/v1/products?price_min=500&price_max=1000"
        )
        assert response.status_code == 200
        data = response.json()
        for product in data["items"]:
            assert 500 <= product["price"] <= 1000

    async def test_products_filter_by_rating(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products?min_rating=4.9")
        assert response.status_code == 200
        data = response.json()
        for product in data["items"]:
            assert product["rating"] >= 4.9


# ==========================================================
# Single Product
# ==========================================================

class TestProductDetail:

    async def test_get_product_success(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products/p1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "p1"
        assert data["name"] == "Belgian Dark Truffle Bar"

    async def test_get_product_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/products/nonexistent")
        assert response.status_code == 404

    async def test_product_has_nutrition(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products/p1")
        assert response.status_code == 200
        data = response.json()
        assert data["nutrition"] is not None
        assert data["nutrition"]["calories"] == "560 kcal"


# ==========================================================
# Product Response Format
# ==========================================================

class TestProductFormat:

    async def test_product_response_camelcase(self, client: AsyncClient):
        await _seed()

        response = await client.get("/api/v1/products/p1")
        data = response.json()
        # Check camelCase fields (frontend compat)
        assert "originalPrice" in data
        assert "hoverImage" in data
        assert "ratingsCount" in data
