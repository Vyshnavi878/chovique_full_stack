import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


async def ensure_superadmin_exists(db: AsyncSession) -> None:
    """
    Ensure the initial superadmin user exists in the database.

    Reads credentials from application configuration (SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD).
    If the superadmin user does not exist, creates the account with role='superadmin',
    is_active=True, is_email_verified=True, and full_name='Enterprise Chief'.
    If the superadmin user already exists, performs no action.
    """
    user_repo = UserRepository(db)
    superadmin_user = await user_repo.get_by_email(settings.SUPERADMIN_EMAIL)

    if not superadmin_user:
        logger.info("Initializing superadmin user (%s)...", settings.SUPERADMIN_EMAIL)
        await user_repo.create(
            email=settings.SUPERADMIN_EMAIL,
            hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
            full_name="Enterprise Chief",
            role="superadmin",
            is_email_verified=True,
            is_active=True,
        )
        await db.commit()
        logger.info("Superadmin user (%s) seeded successfully.", settings.SUPERADMIN_EMAIL)
    else:
        logger.info("Superadmin user (%s) already exists.", settings.SUPERADMIN_EMAIL)
