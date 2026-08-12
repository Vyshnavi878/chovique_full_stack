"""Repository for PlatformSettings — singleton table operations."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.platform_settings import PlatformSettings


SINGLETON_ID = "singleton"


class PlatformSettingsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self) -> PlatformSettings:
        """Return the singleton row, creating it with defaults if it doesn't exist."""
        result = await self.db.execute(
            select(PlatformSettings).where(PlatformSettings.id == SINGLETON_ID)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = PlatformSettings(id=SINGLETON_ID)
            self.db.add(row)
            await self.db.commit()
            await self.db.refresh(row)
        return row

    async def update(self, updates: dict) -> PlatformSettings:
        """Apply a dict of field→value updates to the singleton row."""
        row = await self.get()
        for field, value in updates.items():
            if hasattr(row, field):
                setattr(row, field, value)
        await self.db.commit()
        await self.db.refresh(row)
        return row
