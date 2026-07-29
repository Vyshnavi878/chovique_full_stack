import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.superadmin_service import ensure_superadmin_exists
from app.services.admin_service import ensure_default_banners_exist

logger = logging.getLogger(__name__)


async def seed_database(db: AsyncSession) -> None:
    """Seed sample test data including superadmin and initial hero banners."""
    await ensure_superadmin_exists(db)
    await ensure_default_banners_exist(db)
    logger.info("Test database seeded successfully.")
