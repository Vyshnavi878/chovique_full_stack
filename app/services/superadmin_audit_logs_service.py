import io
import csv
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.audit_log import AuditLog
from app.models.admin_activity_log import AdminActivityLog
from app.models.user import User
from app.schemas.superadmin_audit_logs import AuditLogResponse, AuditLogListResponse


async def record_audit_event(
    db: AsyncSession,
    action: str,
    module: str = "system",
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    ip_address: Optional[str] = "127.0.0.1",
    user_agent: Optional[str] = None,
    request_method: Optional[str] = "POST",
    endpoint: Optional[str] = None,
    status_str: str = "SUCCESS",
    metadata: Optional[Dict[str, Any]] = None,
):
    """Reusable service function to create an immutable audit record."""
    try:
        log_entry = AuditLog(
            user_id=user_id,
            user_role=user_role or "system",
            action=action.strip(),
            module=module.lower().strip(),
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            endpoint=endpoint,
            status=status_str.upper().strip(),
            log_metadata=metadata or {},
        )
        db.add(log_entry)

        # Also create AdminActivityLog record for backward compatibility
        desc = f"{action} in {module}"
        if entity_type and entity_id:
            desc += f" ({entity_type}: {entity_id})"
        admin_log = AdminActivityLog(
            admin_id=user_id,
            action=action.upper().strip(),
            module=module.lower().strip(),
            description=desc,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status_str.upper().strip(),
        )
        db.add(admin_log)

        await db.flush()
    except Exception as e:
        print(f"Failed to record audit log: {e}")


class SuperadminAuditLogsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _to_response(self, log: AuditLog) -> AuditLogResponse:
        u_name = "System Process"
        u_email = None
        u_role = log.user_role or "system"

        if log.user:
            u_name = log.user.full_name
            u_email = log.user.email
            u_role = log.user.role

        formatted_dt = log.created_at.strftime("%d %b %Y, %I:%M %p") if log.created_at else ""

        return AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_name=u_name,
            user_email=u_email,
            user_role=u_role,
            action=log.action,
            module=log.module,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            ip_address=log.ip_address or "192.168.1.10",
            user_agent=log.user_agent,
            request_method=log.request_method or "POST",
            endpoint=log.endpoint or f"/api/v1/{log.module}",
            status=log.status or "SUCCESS",
            metadata=log.log_metadata or {},
            created_at=formatted_dt,
        )

    async def list_audit_logs(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        module: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> AuditLogListResponse:
        """Fetch paginated audit logs with search and multi-filtering."""
        stmt = select(AuditLog).options(selectinload(AuditLog.user))

        if user_id and user_id.strip() and user_id.lower() != "all":
            stmt = stmt.where(AuditLog.user_id == user_id.strip())

        if action and action.strip() and action.lower() != "all":
            stmt = stmt.where(func.lower(AuditLog.action) == action.lower().strip())

        if module and module.strip() and module.lower() != "all":
            stmt = stmt.where(func.lower(AuditLog.module) == module.lower().strip())

        if status_filter and status_filter.strip() and status_filter.lower() != "all":
            stmt = stmt.where(func.lower(AuditLog.status) == status_filter.lower().strip())

        if date_from:
            try:
                dt_from = datetime.fromisoformat(date_from)
                stmt = stmt.where(AuditLog.created_at >= dt_from)
            except ValueError:
                pass

        if date_to:
            try:
                dt_to = datetime.fromisoformat(date_to)
                stmt = stmt.where(AuditLog.created_at <= dt_to)
            except ValueError:
                pass

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.outerjoin(User, AuditLog.user_id == User.id).where(
                or_(
                    AuditLog.action.ilike(pattern),
                    AuditLog.module.ilike(pattern),
                    AuditLog.endpoint.ilike(pattern),
                    AuditLog.entity_id.ilike(pattern),
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        # Count total records
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.db.execute(count_stmt)
        total_count = total_res.scalar_one() or 0

        # Paginated results
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
        logs_res = await self.db.execute(stmt)
        logs = logs_res.scalars().all()

        items = [self._to_response(l) for l in logs]

        return AuditLogListResponse(
            items=items,
            total=total_count,
            page=page,
            limit=limit,
        )

    async def get_audit_log_by_id(self, log_id: str) -> AuditLogResponse:
        """Fetch single audit log detail by ID."""
        stmt = select(AuditLog).options(selectinload(AuditLog.user)).where(AuditLog.id == log_id)
        res = await self.db.execute(stmt)
        log = res.scalars().first()
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit log entry not found.",
            )
        return self._to_response(log)

    async def generate_audit_logs_csv(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        module: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> str:
        """Generate CSV export string for audit logs."""
        list_res = await self.list_audit_logs(
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            action=action,
            module=module,
            status_filter=status_filter,
            search=search,
            page=1,
            limit=10000,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Audit ID",
            "Date & Time",
            "User Name",
            "User Email",
            "Role",
            "Action",
            "Module",
            "Entity Type",
            "Entity ID",
            "IP Address",
            "HTTP Method",
            "Endpoint",
            "Status",
        ])

        for item in list_res.items:
            writer.writerow([
                item.id,
                item.created_at,
                item.user_name,
                item.user_email or "N/A",
                item.user_role,
                item.action,
                item.module,
                item.entity_type or "—",
                item.entity_id or "—",
                item.ip_address,
                item.request_method,
                item.endpoint,
                item.status,
            ])

        return output.getvalue()
