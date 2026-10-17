"""User model — authentication and authorization entity."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Application user with role-based access control.

    Roles:
        viewer     — read-only access to their own analyses
        radiologist — can annotate reports
        admin      — full access, user management

    Security notes:
        - password_hash stores bcrypt hash only, never plaintext
        - is_active gates login; disabled accounts cannot obtain tokens
        - failed_login_count / locked_until implement brute-force protection
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email — used as login identifier",
    )

    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Display username",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the user password — NEVER store plaintext",
    )

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="viewer",
        server_default="viewer",
        index=True,
        comment="Role: viewer | radiologist | admin",
    )

    profession: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="viewer",
        server_default="viewer",
        comment="Self-declared profession; not an authorization role or credential verification",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Disabled users cannot authenticate",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Email verification flag (optional workflow)",
    )

    failed_login_count: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
        nullable=False,
        comment="Consecutive failed login attempts (brute-force guard)",
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until this timestamp after too many failures",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    token_version: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)

    # Relationships
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    annotations = relationship(
        "AnalysisAnnotation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
