import uuid
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.theme import ThemePreset
from app.models.user import User
from app.schemas.superadmin_theme import (
    ThemeCreateRequest,
    ThemeUpdateRequest,
    ThemeResponse,
    ThemeListResponse,
)
from app.services.superadmin_audit_logs_service import record_audit_event

PRESET_SEED_DATA = [
    {
        "id": "preset-chovique-classic",
        "name": "Chovique Classic",
        "description": "Signature chocolate & gold luxury palette",
        "primary_brand_color": "#5A3825",
        "background_color": "#0D090A",
        "luxury_gold_color": "#D4AF37",
        "secondary_accent_color": "#B76E79",
        "text_color": "#F7F7F7",
        "surface_color": "#1A1716",
        "is_active": True,
        "is_preset": True,
    },
    {
        "id": "preset-slate-noir",
        "name": "Slate Noir",
        "description": "Sophisticated gradient from dark slate to charcoal gray",
        "primary_brand_color": "#2C3E50",
        "background_color": "#1A252F",
        "luxury_gold_color": "#BDC3C7",
        "secondary_accent_color": "#7F8C8D",
        "text_color": "#ECF0F1",
        "surface_color": "#2C3E50",
        "is_active": False,
        "is_preset": True,
    },
    {
        "id": "preset-dark-elegance",
        "name": "Dark Elegance",
        "description": "Black-to-gray gradient with warm gold accents",
        "primary_brand_color": "#111111",
        "background_color": "#050505",
        "luxury_gold_color": "#E6C687",
        "secondary_accent_color": "#8A734C",
        "text_color": "#F0E6D2",
        "surface_color": "#1A1A1A",
        "is_active": False,
        "is_preset": True,
    },
    {
        "id": "preset-midnight-premium",
        "name": "Midnight Premium",
        "description": "Deep navy with silver tones — sophisticated & cool",
        "primary_brand_color": "#0F172A",
        "background_color": "#020617",
        "luxury_gold_color": "#94A3B8",
        "secondary_accent_color": "#38BDF8",
        "text_color": "#F8FAFC",
        "surface_color": "#1E293B",
        "is_active": False,
        "is_preset": True,
    },
]


class SuperadminThemeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def seed_preset_themes(self):
        """Ensure 4 preset themes exist in database."""
        for seed in PRESET_SEED_DATA:
            res = await self.db.execute(select(ThemePreset).where(ThemePreset.name == seed["name"]))
            existing = res.scalars().first()
            if not existing:
                theme = ThemePreset(
                    id=seed["id"],
                    name=seed["name"],
                    description=seed["description"],
                    primary_brand_color=seed["primary_brand_color"],
                    background_color=seed["background_color"],
                    luxury_gold_color=seed["luxury_gold_color"],
                    secondary_accent_color=seed["secondary_accent_color"],
                    text_color=seed["text_color"],
                    surface_color=seed["surface_color"],
                    properties_json="{}",
                    is_active=seed["is_active"],
                    is_preset=seed["is_preset"],
                )
                self.db.add(theme)
        await self.db.commit()

    def _to_response(self, theme: ThemePreset) -> ThemeResponse:
        created_str = theme.created_at.strftime("%Y-%m-%d %H:%M:%S") if theme.created_at else ""
        updated_str = theme.updated_at.strftime("%Y-%m-%d %H:%M:%S") if theme.updated_at else ""
        return ThemeResponse(
            id=theme.id,
            name=theme.name,
            description=theme.description,
            primary_brand_color=theme.primary_brand_color,
            background_color=theme.background_color,
            luxury_gold_color=theme.luxury_gold_color,
            secondary_accent_color=theme.secondary_accent_color,
            text_color=theme.text_color,
            surface_color=theme.surface_color,
            is_active=theme.is_active,
            is_preset=theme.is_preset,
            created_at=created_str,
            updated_at=updated_str,
            created_by=theme.created_by,
        )

    async def get_all_themes(self) -> ThemeListResponse:
        await self.seed_preset_themes()
        res = await self.db.execute(select(ThemePreset).order_by(ThemePreset.is_preset.desc(), ThemePreset.created_at.asc()))
        themes = res.scalars().all()
        active_id = next((t.id for t in themes if t.is_active), None)
        return ThemeListResponse(
            items=[self._to_response(t) for t in themes],
            active_theme_id=active_id,
        )

    async def get_theme_by_id(self, theme_id: str) -> ThemeResponse:
        res = await self.db.execute(select(ThemePreset).where(ThemePreset.id == theme_id))
        theme = res.scalars().first()
        if not theme:
            raise HTTPException(status_code=404, detail="Theme preset not found.")
        return self._to_response(theme)

    async def create_theme(self, payload: ThemeCreateRequest, current_user: User) -> ThemeResponse:
        # Check duplicate name
        res = await self.db.execute(select(ThemePreset).where(ThemePreset.name == payload.name.strip()))
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Theme name '{payload.name}' already exists. Please choose a unique name.",
            )

        theme = ThemePreset(
            id=str(uuid.uuid4()),
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            primary_brand_color=payload.primary_brand_color,
            background_color=payload.background_color,
            luxury_gold_color=payload.luxury_gold_color,
            secondary_accent_color=payload.secondary_accent_color,
            text_color=payload.text_color,
            surface_color=payload.surface_color,
            properties_json="{}",
            is_active=False,
            is_preset=False,
            created_by=current_user.id,
        )
        self.db.add(theme)
        await self.db.commit()
        await self.db.refresh(theme)

        # Audit event
        await record_audit_event(
            db=self.db,
            action="THEME_CREATED",
            module="theme_builder",
            user_id=current_user.id,
            user_role=current_user.role,
            entity_type="theme_preset",
            entity_id=theme.id,
            metadata={"theme_name": theme.name},
        )
        await self.db.commit()

        return self._to_response(theme)

    async def update_theme(self, theme_id: str, payload: ThemeUpdateRequest, current_user: User) -> ThemeResponse:
        res = await self.db.execute(select(ThemePreset).where(ThemePreset.id == theme_id))
        theme = res.scalars().first()
        if not theme:
            raise HTTPException(status_code=404, detail="Theme preset not found.")

        if theme.is_preset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preset themes cannot be modified. Create a custom theme copy instead.",
            )

        if payload.name and payload.name.strip() != theme.name:
            dup_res = await self.db.execute(select(ThemePreset).where(ThemePreset.name == payload.name.strip()))
            if dup_res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Theme name '{payload.name}' already exists.",
                )
            theme.name = payload.name.strip()

        if payload.description is not None:
            theme.description = payload.description.strip()

        theme.primary_brand_color = payload.primary_brand_color
        theme.background_color = payload.background_color
        theme.luxury_gold_color = payload.luxury_gold_color
        theme.secondary_accent_color = payload.secondary_accent_color
        theme.text_color = payload.text_color
        theme.surface_color = payload.surface_color

        await self.db.commit()
        await self.db.refresh(theme)

        # Audit event
        await record_audit_event(
            db=self.db,
            action="THEME_UPDATED",
            module="theme_builder",
            user_id=current_user.id,
            user_role=current_user.role,
            entity_type="theme_preset",
            entity_id=theme.id,
            metadata={"theme_name": theme.name},
        )
        await self.db.commit()

        return self._to_response(theme)

    async def preview_theme(self, theme_id: str, current_user: User) -> ThemeResponse:
        theme = await self.get_theme_by_id(theme_id)
        # Audit event
        await record_audit_event(
            db=self.db,
            action="THEME_PREVIEWED",
            module="theme_builder",
            user_id=current_user.id,
            user_role=current_user.role,
            entity_type="theme_preset",
            entity_id=theme.id,
            metadata={"theme_name": theme.name},
        )
        await self.db.commit()
        return theme

    async def apply_theme(self, theme_id: str, current_user: User) -> ThemeResponse:
        res = await self.db.execute(select(ThemePreset).where(ThemePreset.id == theme_id))
        target_theme = res.scalars().first()
        if not target_theme:
            raise HTTPException(status_code=404, detail="Theme preset not found.")

        # Deactivate all themes
        all_res = await self.db.execute(select(ThemePreset))
        all_themes = all_res.scalars().all()
        for t in all_themes:
            t.is_active = (t.id == theme_id)

        await self.db.commit()
        await self.db.refresh(target_theme)

        # Audit event
        await record_audit_event(
            db=self.db,
            action="THEME_APPLIED",
            module="theme_builder",
            user_id=current_user.id,
            user_role=current_user.role,
            entity_type="theme_preset",
            entity_id=target_theme.id,
            metadata={"theme_name": target_theme.name},
        )
        await self.db.commit()

        return self._to_response(target_theme)

    async def reset_theme(self, current_user: User) -> ThemeResponse:
        await self.seed_preset_themes()
        classic_res = await self.db.execute(select(ThemePreset).where(ThemePreset.name == "Chovique Classic"))
        classic_theme = classic_res.scalars().first()

        all_res = await self.db.execute(select(ThemePreset))
        for t in all_res.scalars().all():
            t.is_active = (t.name == "Chovique Classic")

        await self.db.commit()
        if classic_theme:
            await self.db.refresh(classic_theme)

        # Audit event
        await record_audit_event(
            db=self.db,
            action="THEME_RESET",
            module="theme_builder",
            user_id=current_user.id,
            user_role=current_user.role,
            entity_type="theme_preset",
            entity_id=classic_theme.id if classic_theme else "reset",
            metadata={"reset_to": "Chovique Classic"},
        )
        await self.db.commit()

        return self._to_response(classic_theme)

    async def delete_theme(self, theme_id: str, current_user: User) -> dict:
        res = await self.db.execute(select(ThemePreset).where(ThemePreset.id == theme_id))
        theme = res.scalars().first()
        if not theme:
            raise HTTPException(status_code=404, detail="Theme preset not found.")

        if theme.is_preset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System preset themes cannot be deleted.",
            )

        if theme.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active theme cannot be deleted. Please switch to another active theme first.",
            )

        t_name = theme.name
        await self.db.delete(theme)
        await self.db.commit()

        # Audit event
        await record_audit_event(
            db=self.db,
            action="THEME_DELETED",
            module="theme_builder",
            user_id=current_user.id,
            user_role=current_user.role,
            entity_type="theme_preset",
            entity_id=theme_id,
            metadata={"deleted_theme_name": t_name},
        )
        await self.db.commit()

        return {"message": f"Theme '{t_name}' deleted successfully."}
