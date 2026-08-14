import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.session import AsyncSessionLocal
from app.repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request pipeline processing.
    Automatic raw HTTP request logging is disabled to ensure audit_logs contains only
    explicit, meaningful business and security events.
    """

    async def dispatch(self, request: Request, call_next):
        # Always pass OPTIONS preflight and standard requests straight through.
        # Explicit business actions (e.g. coupon creation, profile update, settings changes)
        # record detailed audit log entries directly in their service handlers.
        return await call_next(request)

