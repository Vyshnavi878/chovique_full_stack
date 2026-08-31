from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to attach defensive HTTP security headers to all responses.
    - X-Frame-Options: DENY
    - Content-Security-Policy: frame-ancestors 'none'
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: camera=(), microphone=(), geolocation=()
    - Strict-Transport-Security: max-age=31536000; includeSubDomains (production/HTTPS only)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Clickjacking defense (SEC-001)
        response.headers["X-Frame-Options"] = "DENY"

        # Frame-ancestors CSP (preserve existing CSP directives if present, or set frame-ancestors)
        existing_csp = response.headers.get("Content-Security-Policy")
        if existing_csp:
            if "frame-ancestors" not in existing_csp:
                response.headers["Content-Security-Policy"] = f"{existing_csp}; frame-ancestors 'none'"
        else:
            response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"

        # MIME sniffing protection (SEC-002)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer policy (SEC-002)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (SEC-002)
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # HSTS - only on HTTPS or in non-DEBUG production mode (SEC-002)
        if not settings.DEBUG or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
