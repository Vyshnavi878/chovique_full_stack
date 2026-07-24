import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    change_quantity = Column(Integer, nullable=False)  # positive for restock, negative for sale/adjustment
    reason = Column(String(100), nullable=False)       # 'restock', 'sale', 'adjustment', 'return'
    notes = Column(Text, nullable=True)
    performed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product")
