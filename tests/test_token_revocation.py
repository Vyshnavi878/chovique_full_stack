"""
Unit and Integration Tests for Token Revocation Blocklist and Fail-Closed Redis Resilience (AUTH-003 Remediation).

Verifies:
1. Normal authentication succeeds when Redis is healthy and token is not revoked.
2. Revoked token is rejected with HTTP 401 ("Token has been revoked.") when Redis is healthy.
3. When Redis experiences connection/operational failure, authentication fails securely with HTTP 503 ("Authentication service is temporarily unavailable. Please try again.").
4. Revoked tokens are never allowed to authenticate during Redis disruption (fail-closed security).
5. get_current_user_id direct dependency testing for normal, revoked, and Redis failure states.
"""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import HTTPException

from app.api.deps import get_current_user_id
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio


class TestTokenRevocationBlocklist:

    async def test_valid_unrevoked_token_succeeds(self, client: AsyncClient, mock_redis):
        """Valid token not in Redis blocklist resolves user_id normally."""
        token = create_access_token("user-uuid-12345")
        
        # mock_redis returns None for blocklist:{token}
        user_id = await get_current_user_id(access_token=token)
        assert user_id == "user-uuid-12345"

    async def test_revoked_token_in_blocklist_returns_401(self, client: AsyncClient, mock_redis):
        """Token found in Redis blocklist raises HTTP 401 'Token has been revoked.'"""
        token = create_access_token("user-uuid-12345")
        await mock_redis.setex(f"blocklist:{token}", 900, "1")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(access_token=token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token has been revoked."

    async def test_redis_failure_fails_closed_with_503(self, client: AsyncClient):
        """When Redis is unavailable during blocklist check, fails closed with HTTP 503."""
        token = create_access_token("user-uuid-12345")

        with patch("app.api.deps.redis_client.get", side_effect=ConnectionError("Redis connection refused")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(access_token=token)

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail == "Authentication service is temporarily unavailable. Please try again."

    async def test_redis_failure_on_protected_endpoint_fails_closed(self, client: AsyncClient):
        """Protected endpoint returns 503 and rejects request when Redis is unavailable."""
        token = create_access_token("user-uuid-12345")
        client.cookies.set("access_token", token)

        with patch("app.api.deps.redis_client.get", side_effect=ConnectionError("Redis connection timed out")):
            response = await client.get("/api/v1/users/me")
            assert response.status_code == 503
            assert response.json()["detail"] == "Authentication service is temporarily unavailable. Please try again."
