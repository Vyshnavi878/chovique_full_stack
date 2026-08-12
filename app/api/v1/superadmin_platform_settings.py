"""FastAPI Router — Superadmin Platform Settings."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.platform_settings import (
    PlatformSettingsResponse,
    PlatformSettingsUpdateRequest,
    MaintenanceModeRequest,
    MaintenanceModeResponse,
)
from app.services.platform_settings_service import PlatformSettingsService

router = APIRouter(
    prefix="/superadmin/platform-settings",
    tags=["Superadmin Platform Settings"],
)


@router.get(
    "",
    response_model=PlatformSettingsResponse,
    summary="Get current platform settings",
    description="Returns all platform-wide configuration. Superadmin only.",
)
async def get_platform_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> PlatformSettingsResponse:
    service = PlatformSettingsService(db)
    return await service.get_settings()


@router.put(
    "",
    response_model=PlatformSettingsResponse,
    summary="Update platform settings",
    description="Replace all platform configuration fields. Superadmin only.",
)
async def update_platform_settings(
    payload: PlatformSettingsUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> PlatformSettingsResponse:
    service = PlatformSettingsService(db)
    return await service.update_settings(payload, current_user, request)


@router.post(
    "/maintenance-mode",
    response_model=MaintenanceModeResponse,
    summary="Toggle maintenance mode",
    description=(
        "Enable or disable maintenance mode. Requires `confirmed: true` in the request body. "
        "Superadmin only."
    ),
)
async def toggle_maintenance_mode(
    payload: MaintenanceModeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> MaintenanceModeResponse:
    service = PlatformSettingsService(db)
    return await service.toggle_maintenance_mode(payload, current_user, request)


@router.post(
    "/reset",
    response_model=PlatformSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset platform settings to defaults",
    description="Restore all platform settings to safe factory defaults. Superadmin only.",
)
async def reset_platform_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> PlatformSettingsResponse:
    service = PlatformSettingsService(db)
    return await service.reset_settings(current_user, request)
