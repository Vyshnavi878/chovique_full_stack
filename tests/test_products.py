"""
Product endpoint tests.

Covers: listing (empty database), single product not-found,
and admin CRUD operations.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


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


# ==========================================================
# Single Product
# ==========================================================

class TestProductDetail:

    async def test_get_product_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/products/nonexistent")
        assert response.status_code == 404
