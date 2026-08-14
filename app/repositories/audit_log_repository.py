from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


class AuditLogRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        resource: str | None = None,
        details: str | None = None,
        module: str = "system",
        user_role: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        request_method: str | None = None,
        status: str = "SUCCESS",
        metadata: dict | None = None,
    ) -> AuditLog:
        log_meta = dict(metadata) if metadata else {}
        if details:
            log_meta["details"] = details

        entry = AuditLog(
            user_id=user_id,
            user_role=user_role,
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            request_method=request_method,
            endpoint=resource,
            status=status,
            log_metadata=log_meta if log_meta else None,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_recent_logs(self, limit: int = 50) -> list[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
