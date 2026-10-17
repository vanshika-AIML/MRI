"""Study model — represents an MRI examination session."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Study(Base):
    """An MRI study (examination) linked to a patient.

    Hierarchy: Patient → **Study** → Series → Image
    Side links: Study → Analysis, Study → Embedding
    """

    __tablename__ = "studies"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    study_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
        comment="DICOM Study Instance UID",
    )

    study_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    modality: Mapped[str | None] = mapped_column(
        String(16), nullable=True,
        comment="e.g. MR, CT, PT",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────
    patient = relationship("Patient", back_populates="studies")

    series = relationship(
        "Series",
        back_populates="study",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    analyses = relationship(
        "Analysis",
        back_populates="study",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    embeddings = relationship(
        "Embedding",
        back_populates="study",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Study id={self.id} uid={self.study_uid}>"
