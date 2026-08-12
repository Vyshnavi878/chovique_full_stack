from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.superadmin_audit_logs import AuditLogResponse, AuditLogListResponse
from app.services.superadmin_audit_logs_service import SuperadminAuditLogsService

router = APIRouter(prefix="/superadmin/audit-logs", tags=["Super Admin Audit Logs"])


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List Super Admin Audit Logs",
)
async def list_audit_logs(
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="User ID filter"),
    action: Optional[str] = Query(None, description="Action filter"),
    module: Optional[str] = Query(None, description="Module filter"),
    status: Optional[str] = Query(None, description="Status filter (SUCCESS/FAILURE/DENIED)"),
    search: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Fetch paginated audit logs with date, user, action, module, status filters and search.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAuditLogsService(db)
    return await service.list_audit_logs(
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        module=module,
        status_filter=status,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/export",
    summary="Export Audit Logs CSV",
)
async def export_audit_logs_csv(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Export filtered audit logs history as a CSV file.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAuditLogsService(db)
    csv_content = await service.generate_audit_logs_csv(
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        module=module,
        status_filter=status,
        search=search,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{date_from or 'all'}_to_{date_to or 'all'}.csv"
        },
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    summary="Get Audit Log Detail",
)
async def get_audit_log_by_id(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Fetch single audit log detail by ID.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAuditLogsService(db)
    return await service.get_audit_log_by_id(log_id)
