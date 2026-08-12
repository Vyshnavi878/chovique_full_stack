from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.superadmin_admins import (
    AdminCreateRequest,
    AdminUpdateRequest,
    AdminStatusUpdateRequest,
    AdminPasswordUpdateRequest,
    AdminUserResponse,
    AdminListResponse,
)
from app.services.superadmin_admins_service import SuperadminAdminsService

router = APIRouter(prefix="/superadmin/admins", tags=["Super Admin Admin Management"])


@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Administrator",
)
async def register_admin(
    payload: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Register a new administrator or superadmin account.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAdminsService(db)
    return await service.register_admin(payload, current_user)


@router.get(
    "",
    response_model=AdminListResponse,
    summary="List All Administrators",
)
async def list_admins(
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    role: Optional[str] = Query(None, description="Filter by role: 'admin' or 'superadmin'"),
    status: Optional[str] = Query(None, description="Filter by status: 'active' or 'inactive'"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Fetch paginated list of administrators.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAdminsService(db)
    return await service.list_admins(
        search=search,
        role=role,
        status_filter=status,
        page=page,
        limit=limit,
    )


@router.get(
    "/{admin_id}",
    response_model=AdminUserResponse,
    summary="Get Administrator Details",
)
async def get_admin_by_id(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Get administrator details by ID.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAdminsService(db)
    return await service.get_admin_by_id(admin_id)


@router.put(
    "/{admin_id}",
    response_model=AdminUserResponse,
    summary="Update Administrator Details",
)
async def update_admin(
    admin_id: str,
    payload: AdminUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Update administrator profile details (name, email, phone, role, status).
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAdminsService(db)
    return await service.update_admin(admin_id, payload, current_user)


@router.patch(
    "/{admin_id}/status",
    response_model=AdminUserResponse,
    summary="Update Administrator Status",
)
async def update_admin_status(
    admin_id: str,
    payload: AdminStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Activate or deactivate an administrator account.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAdminsService(db)
    return await service.update_admin_status(admin_id, payload, current_user)


@router.patch(
    "/{admin_id}/password",
    response_model=AdminUserResponse,
    summary="Update Administrator Password",
)
async def update_admin_password(
    admin_id: str,
    payload: AdminPasswordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Securely update an administrator password.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAdminsService(db)
    return await service.update_admin_password(admin_id, payload, current_user)


@router.delete(
    "/{admin_id}",
    summary="Delete Administrator Account",
)
async def delete_admin(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
):
    """
    Delete an administrator account with security guardrail checks.
    Strictly requires 'superadmin' role authorization.
    """
    service = SuperadminAdminsService(db)
    return await service.delete_admin(admin_id, current_user)
