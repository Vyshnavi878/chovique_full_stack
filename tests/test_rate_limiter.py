"""
Unit and Integration Tests for Client IP Detection and Rate Limiter (AUTH-004 Remediation).

Verifies:
1. _get_client_ip properly parses CF-Connecting-IP header.
2. _get_client_ip properly parses X-Real-IP header.
3. _get_client_ip properly parses first IP from comma-separated X-Forwarded-For.
4. _get_client_ip falls back to request.client.host when headers are absent.
5. RateLimiter enforces distinct limits per client IP in Redis.
6. RateLimiter raises HTTP 429 when threshold is exceeded for a given IP.
"""

import os
import pytest
from unittest.mock import MagicMock
from fastapi import Request, HTTPException

from app.middleware.rate_limit_middleware import RateLimiter, _get_client_ip
from app.core.config import settings

pytestmark = pytest.mark.asyncio


class TestClientIPDetection:

    def test_cf_connecting_ip_precedence(self):
        """CF-Connecting-IP is extracted when present."""
        request = MagicMock(spec=Request)
        request.headers = {
            "CF-Connecting-IP": "198.51.100.1",
            "X-Forwarded-For": "203.0.113.50, 10.0.0.1",
            "X-Real-IP": "198.51.100.2",
        }
        assert _get_client_ip(request) == "198.51.100.1"

    def test_x_real_ip_precedence_over_forwarded_for(self):
        """X-Real-IP is extracted when CF-Connecting-IP is absent."""
        request = MagicMock(spec=Request)
        request.headers = {
            "X-Real-IP": "198.51.100.2",
            "X-Forwarded-For": "203.0.113.50, 10.0.0.1",
        }
        assert _get_client_ip(request) == "198.51.100.2"

    def test_x_forwarded_for_first_client_ip(self):
        """First entry in X-Forwarded-For is extracted (client IP before proxy hops)."""
        request = MagicMock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "203.0.113.50, 10.0.0.1, 172.16.0.1",
        }
        assert _get_client_ip(request) == "203.0.113.50"

    def test_fallback_to_request_client_host(self):
        """Direct connection without headers falls back to request.client.host."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"
        assert _get_client_ip(request) == "192.168.1.100"

    def test_fallback_to_localhost_when_no_client(self):
        """Fallback to 127.0.0.1 when client info is None."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == "127.0.0.1"


class TestRateLimiterFunctionality:

    async def test_rate_limiter_distinct_ips_have_separate_counters(self, mock_redis, monkeypatch):
        """Requests from different IPs do not exhaust each other's rate limits."""
        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setenv("TESTING", "0")

        limiter = RateLimiter(times=2, seconds=60)

        # Request from IP 1
        req1 = MagicMock(spec=Request)
        req1.headers = {"X-Forwarded-For": "1.1.1.1"}
        req1.url = MagicMock()
        req1.url.path = "/api/v1/auth/login"

        # Request from IP 2
        req2 = MagicMock(spec=Request)
        req2.headers = {"X-Forwarded-For": "2.2.2.2"}
        req2.url = MagicMock()
        req2.url.path = "/api/v1/auth/login"

        # IP 1 uses 2 attempts (limit is 2)
        await limiter(req1)
        await limiter(req1)

        # IP 1's 3rd attempt is blocked (HTTP 429)
        with pytest.raises(HTTPException) as exc_info:
            await limiter(req1)
        assert exc_info.value.status_code == 429

        # IP 2 can still make attempts (unaffected by IP 1)
        await limiter(req2)
        await limiter(req2)

        # IP 2's 3rd attempt is blocked
        with pytest.raises(HTTPException) as exc_info:
            await limiter(req2)
        assert exc_info.value.status_code == 429
