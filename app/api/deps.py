"""Dependency helpers for API routes."""

from typing import Optional

from fastapi import Cookie, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository


def _extract_token(
    access_token: Optional[str],
    authorization: Optional[str],
) -> Optional[str]:
    """Accept either the httponly access_token cookie or a Bearer header."""

    if access_token:
        return access_token

    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()

    return None


async def get_current_user_id(
    access_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    Resolve the authenticated user's id from the access token.

    Supports both the httponly `access_token` cookie (set by the backend on
    login/register) and an `Authorization: Bearer <token>` header, so either
    client-side auth strategy works.
    """

    token = _extract_token(access_token, authorization)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    from app.db.redis import redis_client
    import logging
    import redis.exceptions

    is_blocked = False
    try:
        is_blocked = await redis_client.get(f"blocklist:{token}")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Redis connection error: {e}. Skipping token blocklist check. Is Redis running?")
        is_blocked = False
        
    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the full, active User record for the authenticated request."""

    user = await UserRepository(db).get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    return user


# ==========================================================
# Role-Based Access Control
# ==========================================================

def require_role(*allowed_roles: str):
    """
    Dependency factory that returns a dependency requiring
    the current user to have one of the specified roles.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(
            user: User = Depends(require_role("admin", "superadmin")),
        ):
            ...
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user

    return _check_role


# Convenience shortcut for admin-only routes
get_current_admin = require_role("admin", "superadmin")
