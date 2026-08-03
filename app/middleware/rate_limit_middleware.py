"""Rate limit middleware."""

from fastapi import Request, HTTPException, status
from app.db.redis import redis_client

def RateLimiter(times: int, seconds: int):
    """
    FastAPI dependency for rate limiting using Redis.
    Limits requests based on the client's IP address and the requested path.
    """
    async def _rate_limit(request: Request):
        ip = request.client.host if request.client else "127.0.0.1"
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
