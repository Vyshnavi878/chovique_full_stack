import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    JSON,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    # ==========================
    # Primary Key
    # ==========================
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ==========================
    # Core Fields
    # ==========================
    name = Column(String(200), nullable=False, index=True)
    slug = Column(String(220), unique=True, nullable=False, index=True)
    category = Column(
        Enum(
            "dark", "milk", "white", "gift", "beverage",
            name="product_category",
        ),
        nullable=False,
        index=True,
    )
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    weight = Column(String(50), nullable=True)
    stock = Column(Integer, default=100, nullable=False)

    # ==========================
    # Details
    # ==========================
    description = Column(Text, nullable=True)
    ingredients = Column(Text, nullable=True)
    nutrition = Column(JSON, nullable=True)

    # ==========================
    # Display
    # ==========================
    badge = Column(
        String(50),
        nullable=True,
    )


    image = Column(Text, nullable=True)
    hover_image = Column(Text, nullable=True)
    images = Column(JSON, nullable=True, default=list)

    # ==========================
    # Ratings
    # ==========================
    rating = Column(Float, default=0.0, nullable=False)
    ratings_count = Column(Integer, default=0, nullable=False)

    # ==========================
    # Management & Flags
    # ==========================
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_bestseller = Column(Boolean, default=False, nullable=False)
    is_new_arrival = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # ==========================
    # Audit
    # ==========================
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
