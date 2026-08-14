import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.superadmin_service import ensure_superadmin_exists

logger = logging.getLogger(__name__)


async def seed_database(db: AsyncSession) -> None:
    """Seed superadmin user credentials only."""
    await ensure_superadmin_exists(db)
    logger.info("Superadmin user seeded successfully.")
