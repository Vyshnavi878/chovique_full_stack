from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_role = Column(String(50), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    module = Column(String(100), nullable=False, default="system", index=True)
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    endpoint = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="SUCCESS", index=True)
    
    # Mapped as log_metadata to avoid collision with Base.metadata
    log_metadata = Column("metadata", JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user = relationship("User", foreign_keys=[user_id])

    def __init__(self, **kwargs):
        resource = kwargs.pop("resource", None)
        details = kwargs.pop("details", None)
        super().__init__(**kwargs)
        if resource is not None:
            self.endpoint = resource
        if details is not None:
            if self.log_metadata is None or not isinstance(self.log_metadata, dict):
                self.log_metadata = {}
            self.log_metadata["details"] = details

    @property
    def resource(self) -> str | None:
        return self.endpoint or self.module

    @resource.setter
    def resource(self, value: str | None) -> None:
        self.endpoint = value

    @property
    def details(self) -> str | None:
        if self.log_metadata and isinstance(self.log_metadata, dict):
            return self.log_metadata.get("details") or self.log_metadata.get("description")
        return None

    @details.setter
    def details(self, value: str | None) -> None:
        if self.log_metadata is None or not isinstance(self.log_metadata, dict):
            self.log_metadata = {}
        self.log_metadata["details"] = value

