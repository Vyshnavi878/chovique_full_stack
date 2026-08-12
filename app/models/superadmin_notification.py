"""SQLAlchemy model for Superadmin-only notifications."""
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SuperadminNotification(Base):
    """
    Separate notification table exclusively for Super Admin (website owner) events.

    Categories:
        SECURITY          - Failed logins, suspicious activity, security config changes
        ADMIN_MANAGEMENT  - Admin created/updated/deleted/activated/deactivated
        PLATFORM_SYSTEM   - Maintenance mode, critical errors, payment gateway issues
        BUSINESS          - Revenue anomalies, business threshold alerts

    Severities:
        INFO, WARNING, CRITICAL
    """
    __tablename__ = "superadmin_notifications"

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)

    # category: SECURITY | ADMIN_MANAGEMENT | PLATFORM_SYSTEM | BUSINESS
    category = Column(String(50), nullable=False, index=True)

    # severity: INFO | WARNING | CRITICAL
    severity = Column(String(20), nullable=False, default="INFO", index=True)

    is_read = Column(Boolean, nullable=False, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Optional: link to the entity that triggered the notification
    related_entity_type = Column(String(100), nullable=True)   # e.g. "admin_user", "platform_settings"
    related_entity_id = Column(String(100), nullable=True)

    # Optional: the Admin user involved (e.g. the admin that was created/deleted)
    related_user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationship for the related admin user (for detail view)
    related_user = relationship("User", foreign_keys=[related_user_id])

    __table_args__ = (
        Index("ix_sa_notif_category_is_read", "category", "is_read"),
        Index("ix_sa_notif_severity_created", "severity", "created_at"),
    )
