"""Series model — an MRI series within a study."""
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Series(Base):
    """A single MRI series inside a study.

    Hierarchy: Patient → Study → **Series** → Image
    """

    __tablename__ = "series"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    series_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
        comment="DICOM Series Instance UID",
    )

    series_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    body_part: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="e.g. BRAIN, SPINE, KNEE",
    )

    # ── Relationships ──────────────────────────────────────────────
    study = relationship("Study", back_populates="series")

    images = relationship(
        "Image",
        back_populates="series",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Series id={self.id} uid={self.series_uid}>"
