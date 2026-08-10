"""
Database session configuration.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base

# Import all models so they are registered with SQLAlchemy metadata
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.banner import Banner  # noqa: F401
from app.models.testimonial import Testimonial  # noqa: F401
from app.models.site_config import SiteConfig  # noqa: F401
from app.models.address import CustomerAddress  # noqa: F401
from app.models.coupon import Coupon  # noqa: F401
from app.models.order import Order, OrderItem, OrderSequence  # noqa: F401
from app.models.ticket import SupportTicket  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.contact import ContactMessage  # noqa: F401
from app.models.review import ProductReview  # noqa: F401
from app.models.reel import InstagramReel  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.cart import Cart, CartItem  # noqa: F401
from app.models.wishlist import WishlistItem  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.refund import Refund  # noqa: F401
from app.models.inventory import InventoryLog  # noqa: F401
from app.models.faq import FAQ  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.offline_sale import OfflineSale  # noqa: F401
from app.models.theme import ThemePreset  # noqa: F401
from app.models.wallet import UserWallet, CoinTransaction  # noqa: F401
# ==========================================================
# Create Async Engine
# ==========================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,
)

# ==========================================================
# Session Factory
# ==========================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

# ==========================================================
# Database Initialization
# ==========================================================


from sqlalchemy import text


async def init_db() -> None:
    """
    Create database tables if they do not already exist and run schema migrations.
    """

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        alter_statements = [
            # Products
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS stock INTEGER NOT NULL DEFAULT 100;",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT FALSE;",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_bestseller BOOLEAN NOT NULL DEFAULT FALSE;",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS is_new_arrival BOOLEAN NOT NULL DEFAULT FALSE;",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS images JSON;",
            # Orders
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) NOT NULL DEFAULT 'PENDING';",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS invoice_url VARCHAR(500);",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS tax DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(50);",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coupon_discount DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coins_used INTEGER NOT NULL DEFAULT 0;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coin_discount DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coins_earned INTEGER NOT NULL DEFAULT 0;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_option VARCHAR(100) NOT NULL DEFAULT 'Standard Delivery';",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(100) NOT NULL DEFAULT 'UPI';",
            # Product Reviews
            "ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved';",
            "ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;",
            # Testimonials
            "ALTER TABLE testimonials ADD COLUMN IF NOT EXISTS user_id VARCHAR(36);",
            "ALTER TABLE testimonials ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved';",
            "ALTER TABLE testimonials ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;",
        ]
        for stmt in alter_statements:
            try:
                await connection.execute(text(stmt))
            except Exception:
                pass



# ==========================================================
# Dependency
# ==========================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
