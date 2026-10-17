"""AnalysisAnnotation model — user-authored notes on analysis reports.

Separates model-generated findings from human-authored annotations so
model outputs are never silently overwritten by user edits.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalysisAnnotation(Base):
    """A user-authored annotation attached to an analysis run.

    Key safety invariants:
      - The parent Analysis record is never modified; this is a separate entity.
      - is_original=True entries reflect model outputs only.
      - User text is always stored in annotation_text; model summaries remain in
        the parent analysis.result JSONB blob untouched.
    """

    __tablename__ = "analysis_annotations"

    analysis_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="analysis_id hex string from AnalysisResponse (not a FK to keep it decoupled from optional DB)",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Annotating user",
    )

    annotation_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Free-text annotation by the authorized user",
    )

    field_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Optional: specific field being annotated (e.g. 'summary', 'severity_note')",
    )

    is_original: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="True only for system-generated entries; user edits are always False",
    )

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        comment="Monotonically increasing edit version",
    )

    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_annotations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Points to newer version when this annotation is superseded",
    )

    # Relationships
    user = relationship("User", back_populates="annotations")

    def __repr__(self) -> str:
        return (
            f"<AnalysisAnnotation id={self.id} analysis={self.analysis_id} "
            f"user={self.user_id} v{self.version}>"
        )
