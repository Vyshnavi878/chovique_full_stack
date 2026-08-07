import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Unauthenticated public endpoints where no session cookie exists to be forged,
# so CSRF validation is unnecessary and skipped.
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/google",
    "/api/v1/auth/verify-otp",
    "/api/v1/auth/resend-otp",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/resend-forgot-otp",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/refresh",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        safe_methods = {"GET", "HEAD", "OPTIONS"}

        if request.method not in safe_methods:
            # Normalize path (strip trailing slashes for robust matching)
            raw_path = request.url.path
            normalized_path = raw_path.rstrip("/") if raw_path != "/" else "/"

            # Skip CSRF check ONLY for unauthenticated public endpoints
            if raw_path not in CSRF_EXEMPT_PATHS and normalized_path not in CSRF_EXEMPT_PATHS:
                csrf_cookie = request.cookies.get("csrf_token")
                csrf_header = request.headers.get("x-csrf-token") or request.headers.get("X-CSRF-Token")

                if (
                    not csrf_cookie
                    or not csrf_header
                    or not secrets.compare_digest(csrf_cookie, csrf_header)
                ):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF token validation failed"}
                    )

        response = await call_next(request)
        return response
