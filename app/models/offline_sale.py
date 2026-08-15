import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OfflineSale(Base):
    __tablename__ = "offline_sales"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    receipt_id = Column(String(100), unique=True, nullable=False, index=True)

    # Company Details
    company_name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=False)

    # Transaction Details
    payment_method = Column(String(100), nullable=False, default="Cash")
    subtotal = Column(Float, nullable=False, default=0.0)
    discount = Column(Float, nullable=False, default=0.0)
    tax = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="Completed")

    # Backward compatibility fields (for older superadmin revenue queries)
    product_name = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=True, default=1)
    total_price = Column(Float, nullable=True, default=0.0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    items = relationship("OfflineSaleItem", back_populates="sale", cascade="all, delete-orphan", lazy="selectin")


class OfflineSaleItem(Base):
    __tablename__ = "offline_sale_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sale_id = Column(String(36), ForeignKey("offline_sales.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True)
    unit_price = Column(Float, nullable=False, default=0.0)
    quantity = Column(Integer, nullable=False, default=1)
    line_total = Column(Float, nullable=False, default=0.0)

    sale = relationship("OfflineSale", back_populates="items")
    product = relationship("Product", lazy="selectin")

