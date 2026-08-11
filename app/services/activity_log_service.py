from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin_activity_log import AdminActivityLog
from app.models.user import User
from app.schemas.admin_activity_log import ActivityLogResponse, ActivityLogListResponse


async def log_admin_activity(
    db: AsyncSession,
    admin_id: Optional[str],
    action: str,
    module: str,
    description: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "SUCCESS",
):
    """Helper to log admin activity in the database."""
    try:
        log_entry = AdminActivityLog(
            admin_id=admin_id,
            action=action.upper().strip(),
            module=module.lower().strip(),
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status.upper().strip(),
        )
        db.add(log_entry)
        await db.flush()
    except Exception as e:
        print(f"Failed to create admin activity log: {e}")


class ActivityLogService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_activity_logs(
        self,
        page: int = 1,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> ActivityLogListResponse:
        query = select(AdminActivityLog).options(selectinload(AdminActivityLog.admin))
        conditions = []

        # Module filter
        if module and module.strip() and module.lower() != "all":
            conditions.append(func.lower(AdminActivityLog.module) == module.lower().strip())

        # Action filter
        if action and action.strip() and action.lower() != "all":
            conditions.append(func.lower(AdminActivityLog.action) == action.lower().strip())

        # Status filter
        if status and status.strip() and status.lower() != "all":
            conditions.append(func.lower(AdminActivityLog.status) == status.lower().strip())

        # Date range filter
        if start_date:
            try:
                dt_start = datetime.fromisoformat(start_date)
                conditions.append(AdminActivityLog.created_at >= dt_start)
            except ValueError:
                pass

        if end_date:
            try:
                dt_end = datetime.fromisoformat(end_date)
                conditions.append(AdminActivityLog.created_at <= dt_end)
            except ValueError:
                pass

        # Search filter (description, admin name, admin email)
        if search and search.strip():
            s_pattern = f"%{search.strip()}%"
            # Join with user table if needed for search
            query = query.outerjoin(User, AdminActivityLog.admin_id == User.id)
            conditions.append(
                or_(
                    AdminActivityLog.description.ilike(s_pattern),
                    AdminActivityLog.action.ilike(s_pattern),
                    AdminActivityLog.module.ilike(s_pattern),
                    User.full_name.ilike(s_pattern),
                    User.email.ilike(s_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one_or_none() or 0

        # Pagination & Ordering
        offset = (page - 1) * limit
        query = query.order_by(AdminActivityLog.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        items: List[ActivityLogResponse] = []
        for log in logs:
            items.append(
                ActivityLogResponse(
                    id=log.id,
                    admin_id=log.admin_id,
                    admin_name=log.admin.full_name if log.admin else "System Admin",
                    admin_email=log.admin.email if log.admin else None,
                    action=log.action,
                    module=log.module,
                    description=log.description,
                    ip_address=log.ip_address,
                    user_agent=log.user_agent,
                    status=log.status,
                    created_at=log.created_at,
                )
            )

        return ActivityLogListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
        )
