import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.theme import ThemePreset
from app.schemas.theme import ThemePresetPayload, ThemePresetResponse

class ThemeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_themes(self) -> list[ThemePresetResponse]:
        result = await self.db.execute(select(ThemePreset))
        themes = result.scalars().all()
        return [
            ThemePresetResponse(
                id=t.id,
                name=t.name,
                properties_json=t.properties_json,
                is_active=t.is_active,
            )
            for t in themes
        ]

    async def get_active_theme(self) -> ThemePresetResponse | None:
        result = await self.db.execute(select(ThemePreset).where(ThemePreset.is_active == True))
        t = result.scalars().first()
        if not t:
            return None
        return ThemePresetResponse(
            id=t.id,
            name=t.name,
            properties_json=t.properties_json,
            is_active=t.is_active,
        )

    async def save_theme(self, payload: ThemePresetPayload) -> ThemePresetResponse:
        theme = ThemePreset(
            id=str(uuid.uuid4()),
            name=payload.name,
            properties_json=payload.properties_json,
            is_active=False
        )
        self.db.add(theme)
        await self.db.commit()
        await self.db.refresh(theme)
        return ThemePresetResponse(
            id=theme.id,
            name=theme.name,
            properties_json=theme.properties_json,
            is_active=theme.is_active
        )

    async def set_active_theme(self, theme_id: str) -> bool:
        # Deactivate all
        result = await self.db.execute(select(ThemePreset).where(ThemePreset.is_active == True))
        active_themes = result.scalars().all()
        for t in active_themes:
            t.is_active = False
            
        # Activate target
        result = await self.db.execute(select(ThemePreset).where(ThemePreset.id == theme_id))
        target = result.scalars().first()
        if not target:
            await self.db.commit()
            return False
            
        target.is_active = True
        await self.db.commit()
        return True

    async def delete_theme(self, theme_id: str) -> bool:
        result = await self.db.execute(select(ThemePreset).where(ThemePreset.id == theme_id))
        theme = result.scalars().first()
        if not theme:
            return False
        
        await self.db.delete(theme)
        await self.db.commit()
        return True
