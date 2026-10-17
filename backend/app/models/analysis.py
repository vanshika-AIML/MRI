"""Analysis model — AI analysis results on MRI data."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Analysis(Base):
    """An AI analysis run against a study and/or image.

    The ``result`` column uses JSONB so different model types can store
    arbitrary structured output without rigid schema changes.

    Status lifecycle::

        pending → running → completed
                          → failed
    """

    __tablename__ = "analyses"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("images.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    analysis_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="e.g. abnormality_detection, enhancement_quality",
    )

    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending",
        index=True,
        comment="pending | running | completed | failed",
    )

    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Relationships ──────────────────────────────────────────────
    study = relationship("Study", back_populates="analyses")

    def __repr__(self) -> str:
        return (
            f"<Analysis id={self.id} type={self.analysis_type} "
            f"status={self.status}>"
        )
