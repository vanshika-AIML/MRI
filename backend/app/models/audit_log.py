"""AuditLog model — immutable record of security-sensitive and clinically relevant actions."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuditLog(Base):
    """Append-only log of security and clinical actions.

    Intended as an immutable audit trail — entries should never be updated
    or deleted via application code.  Use PostgreSQL row-level security or
    a separate append-only table policy in production.

    Action categories:
        auth.*     — login, logout, register, password_change, account_locked
        analysis.* — analysis_run, analysis_annotate
        user.*     — profile_update, role_change, account_deactivate
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Acting user — NULL for unauthenticated or deleted-user events",
    )

    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Dot-separated action key, e.g. auth.login_success",
    )

    resource_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="e.g. analysis, user, annotation",
    )

    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="ID of the resource acted upon",
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP (IPv4 or IPv6)",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User-Agent header (truncated for storage)",
    )

    outcome: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="success",
        comment="success | failure | error",
    )

    details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Supplemental structured context — MUST NOT contain passwords or tokens",
    )

    # Note: created_at from Base acts as the immutable event timestamp
    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} outcome={self.outcome}>"
