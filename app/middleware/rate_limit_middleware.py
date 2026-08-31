import os
from fastapi import Request, HTTPException, status
from app.db.redis import redis_client
from app.core.config import settings


def _get_client_ip(request: Request) -> str:
    """
    Extract the effective client IP address.
    Checks reverse-proxy headers in priority order (Render / Cloudflare / Nginx),
    falling back to request.client.host for direct connections.
    """
    cf_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    x_real_ip = request.headers.get("X-Real-IP") or request.headers.get("x-real-ip")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()

    forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def RateLimiter(times: int, seconds: int):
    """
    FastAPI dependency for rate limiting using Redis.
    Limits requests based on the client's IP address and the requested path.
    Bypassed during automated test execution or DEBUG mode.
    """
    async def _rate_limit(request: Request):
        if settings.DEBUG or os.environ.get("TESTING", "").lower() in ("true", "1"):
            return

        ip = _get_client_ip(request)
        path = request.url.path
        key = f"rate_limit:{path}:{ip}"
        
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, seconds)
            
        if current > times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )
    return _rate_limit
