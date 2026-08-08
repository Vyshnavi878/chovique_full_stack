import uuid
import random
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


import secrets

def generate_order_id():
    return f"ORD-{secrets.randbelow(90000) + 10000}-{str(uuid.uuid4())[:4].upper()}"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_order_id)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    total = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    shipping = Column(Float, default=0.0, nullable=False)
    tax = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="Processing", nullable=False)
    shipping_address = Column(JSON, nullable=False)
    delivery_option = Column(String(100), default="Standard Delivery", nullable=False)
    payment_method = Column(String(100), default="UPI", nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
