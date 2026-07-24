import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.session import AsyncSessionLocal
from app.repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records sensitive admin API operations into audit_logs table.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Record admin & write operations
        path = request.url.path
        method = request.method

        if (path.startswith("/api/v1/admin") or method in ("POST", "PUT", "PATCH", "DELETE")) and not path.endswith("/health"):
            if 200 <= response.status_code < 300:
                client_ip = request.client.host if request.client else "unknown"
                try:
                    async with AsyncSessionLocal() as session:
                        audit_repo = AuditLogRepository(session)
                        await audit_repo.log(
                            action=f"{method} {path}",
                            ip_address=client_ip,
                            resource=path,
                        )
                except Exception as e:
                    logger.debug("Failed to record audit log: %s", e)

        return response
