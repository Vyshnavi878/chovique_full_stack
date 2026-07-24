import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site_config import SiteConfig


class SiteConfigRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # Get Value by Key
    # ==========================================================

    async def get(self, key: str) -> dict | list | str | None:

        result = await self.db.execute(
            select(SiteConfig).where(SiteConfig.key == key)
        )

        config = result.scalar_one_or_none()

        if config is None:
            return None

        try:
            return json.loads(config.value)
        except (json.JSONDecodeError, TypeError):
            return config.value

    # ==========================================================
    # Set Value
    # ==========================================================

    async def set(self, key: str, value) -> None:

        serialized = (
            json.dumps(value)
            if isinstance(value, (dict, list))
            else str(value)
        )

        existing = await self.db.execute(
            select(SiteConfig).where(SiteConfig.key == key)
        )

        config = existing.scalar_one_or_none()

        if config:
            config.value = serialized
        else:
            config = SiteConfig(key=key, value=serialized)
            self.db.add(config)

        await self.db.commit()

    # ==========================================================
    # Get Multiple Keys
    # ==========================================================

    async def get_many(self, keys: list[str]) -> dict:

        result = await self.db.execute(
            select(SiteConfig).where(SiteConfig.key.in_(keys))
        )

        configs = result.scalars().all()

        data = {}
        for config in configs:
            try:
                data[config.key] = json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                data[config.key] = config.value

        return data

    # ==========================================================
    # Count
    # ==========================================================

    async def count(self) -> int:

        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count()).select_from(SiteConfig)
        )

        return result.scalar() or 0
