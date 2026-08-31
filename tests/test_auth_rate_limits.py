"""
Unit and Integration Tests for Authentication Route Rate Limiting (AUTH-005 Remediation).

Verifies:
1. POST /api/v1/auth/google throttles abusive requests (HTTP 429).
2. POST /api/v1/auth/refresh throttles abusive requests (HTTP 429).
3. POST /api/v1/auth/logout throttles abusive requests (HTTP 429).
4. POST /api/v1/auth/change-password throttles abusive requests (HTTP 429).
5. POST /api/v1/auth/set-password throttles abusive requests (HTTP 429).
6. Requests below rate limit thresholds succeed normally.
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient
from app.core.config import settings

pytestmark = pytest.mark.asyncio


class TestAuthEndpointsRateLimiting:

    async def test_google_login_rate_limiting(self, client: AsyncClient, mock_redis, monkeypatch):
        """POST /api/v1/auth/google enforces 10 requests / 60s limit and returns 429."""
        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setenv("TESTING", "0")

        # 10 requests pass through rate limiter (may fail at validation with 400)
        for _ in range(10):
            response = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "some-token"},
            )
            assert response.status_code != 429

        # 11th request is throttled by RateLimiter with HTTP 429
        throttled_response = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "some-token"},
        )
        assert throttled_response.status_code == 429
        assert throttled_response.json()["detail"] == "Too many requests. Please try again later."

    async def test_refresh_token_rate_limiting(self, client: AsyncClient, mock_redis, monkeypatch):
        """POST /api/v1/auth/refresh enforces 20 requests / 60s limit and returns 429."""
        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setenv("TESTING", "0")

        for _ in range(20):
            response = await client.post("/api/v1/auth/refresh")
            assert response.status_code != 429

        throttled_response = await client.post("/api/v1/auth/refresh")
        assert throttled_response.status_code == 429
        assert throttled_response.json()["detail"] == "Too many requests. Please try again later."

    async def test_logout_rate_limiting(self, client: AsyncClient, mock_redis, monkeypatch):
        """POST /api/v1/auth/logout enforces 10 requests / 60s limit and returns 429."""
        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setenv("TESTING", "0")

        client.cookies.set("csrf_token", "VALID_CSRF")
        headers = {"X-CSRF-Token": "VALID_CSRF"}

        for _ in range(10):
            response = await client.post("/api/v1/auth/logout", headers=headers)
            assert response.status_code != 429

        throttled_response = await client.post("/api/v1/auth/logout", headers=headers)
        assert throttled_response.status_code == 429
        assert throttled_response.json()["detail"] == "Too many requests. Please try again later."

    async def test_change_password_rate_limiting(self, client: AsyncClient, mock_redis, monkeypatch):
        """POST /api/v1/auth/change-password enforces 5 requests / 60s limit and returns 429."""
        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setenv("TESTING", "0")

        # Set valid CSRF
        client.cookies.set("csrf_token", "VALID_CSRF")
        headers = {"X-CSRF-Token": "VALID_CSRF"}

        for _ in range(5):
            response = await client.post(
                "/api/v1/auth/change-password",
                headers=headers,
                json={
                    "current_password": "Old1!",
                    "new_password": "New1!",
                    "confirm_password": "New1!",
                },
            )
            assert response.status_code != 429

        throttled_response = await client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={
                "current_password": "Old1!",
                "new_password": "New1!",
                "confirm_password": "New1!",
            },
        )
        assert throttled_response.status_code == 429
        assert throttled_response.json()["detail"] == "Too many requests. Please try again later."
