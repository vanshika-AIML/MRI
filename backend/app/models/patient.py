"""Patient model — top-level entity in the MRI domain hierarchy."""
import uuid

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Patient(Base):
    """A patient who undergoes MRI examinations.

    Only an opaque external identifier is stored; no PII lives in
    this table by design.  Clinical identity resolution is handled
    by upstream systems.

    Hierarchy: Patient → Study → Series → Image
    """

    __tablename__ = "patients"

    external_patient_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True,
        comment="External patient identifier from upstream clinical system",
    )

    # ── Relationships ──────────────────────────────────────────────
    studies = relationship(
        "Study",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} ext={self.external_patient_id}>"
