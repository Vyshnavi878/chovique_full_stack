"""
Unit & Integration Tests for Phase 6 Browser & Client-Side Security Fixes:
1. CORS-001: Explicit Allowed Origins (No arbitrary .vercel.app wildcard regex matching).
2. SEC-001: Clickjacking Defense (X-Frame-Options: DENY and CSP frame-ancestors 'none').
3. SEC-002: Defense-in-depth Security Headers (X-Content-Type-Options, Referrer-Policy, Permissions-Policy).
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestBrowserSecurityHeaders:

    async def test_security_headers_present_on_api_responses(self, client: AsyncClient):
        """Verify SEC-001 and SEC-002 defense-in-depth headers are attached to API responses."""
        response = await client.get("/api/v1/home")
        assert response.status_code == 200

        # Clickjacking Protection (SEC-001)
        assert response.headers.get("x-frame-options") == "DENY"
        assert "frame-ancestors 'none'" in response.headers.get("content-security-policy", "")

        # MIME sniffing protection (SEC-002)
        assert response.headers.get("x-content-type-options") == "nosniff"

        # Referrer policy (SEC-002)
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

        # Permissions policy (SEC-002)
        assert response.headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=()"

    async def test_cors_explicit_allowed_origin_succeeds(self, client: AsyncClient):
        """Verify configured allowed origins receive CORS allow headers with credentials."""
        response = await client.options(
            "/api/v1/home",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert response.headers.get("access-control-allow-credentials") == "true"

    async def test_cors_arbitrary_vercel_subdomain_rejected(self, client: AsyncClient):
        """Verify arbitrary .vercel.app subdomains (CORS-001) are NOT allowed."""
        response = await client.options(
            "/api/v1/home",
            headers={
                "Origin": "https://attacker-app.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Untrusted origin must not be reflected in access-control-allow-origin
        assert response.headers.get("access-control-allow-origin") != "https://attacker-app.vercel.app"
