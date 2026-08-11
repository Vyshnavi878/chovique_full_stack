import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    
    coupon_type = Column(String(50), default="CUSTOMER", nullable=False) # CUSTOMER or INFLUENCER
    discount_type = Column(String(50), default="PERCENTAGE", nullable=False) 
    
    discount_percent = Column(Float, default=0.0, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    
    maximum_discount_amount = Column(Float, default=0.0, nullable=False)
    minimum_order_amount = Column(Float, default=0.0, nullable=False)
    
    start_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    usage_limit = Column(Integer, default=0, nullable=False)
    per_user_usage_limit = Column(Integer, default=1, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    rules = relationship("CouponEligibilityRule", back_populates="coupon", cascade="all, delete-orphan", lazy="selectin")
    users = relationship("CouponUser", back_populates="coupon", cascade="all, delete-orphan", lazy="selectin")
    products = relationship("CouponProduct", back_populates="coupon", cascade="all, delete-orphan", lazy="selectin")
    categories = relationship("CouponCategory", back_populates="coupon", cascade="all, delete-orphan", lazy="selectin")
    usages = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan", lazy="selectin")


class CouponEligibilityRule(Base):
    __tablename__ = "coupon_eligibility_rules"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type = Column(String(50), nullable=False)
    rule_value = Column(String(255), nullable=True)
    
    coupon = relationship("Coupon", back_populates="rules")


class CouponUser(Base):
    __tablename__ = "coupon_users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    coupon = relationship("Coupon", back_populates="users")
    user = relationship("User")


class CouponProduct(Base):
    __tablename__ = "coupon_products"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    coupon = relationship("Coupon", back_populates="products")
    product = relationship("Product")


class CouponCategory(Base):
    __tablename__ = "coupon_categories"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    coupon = relationship("Coupon", back_populates="categories")
    category = relationship("Category")


class CouponUsage(Base):
    __tablename__ = "coupon_usage"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    discount_amount = Column(Float, nullable=False)
    status = Column(String(50), default="APPLIED", nullable=False)
    used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    coupon = relationship("Coupon", back_populates="usages")
    user = relationship("User")
    order = relationship("Order")
