"""Image model — an individual MRI slice / image asset."""
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Image(Base):
    """A single MRI image or slice stored as a file reference.

    Binary MRI data is **not** stored inside PostgreSQL.
    Only the path / object-storage key is persisted.

    Hierarchy: Patient → Study → Series → **Image**
    """

    __tablename__ = "images"

    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sop_instance_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
        comment="DICOM SOP Instance UID",
    )

    file_path: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="Path or object-storage key to the image file",
    )

    file_format: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="e.g. DICOM, NIfTI, PNG",
    )

    slice_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Relationships ──────────────────────────────────────────────
    series = relationship("Series", back_populates="images")

    # updated_at is not meaningful for immutable image records,
    # but it is inherited from Base; set to None by default.

    def __repr__(self) -> str:
        return f"<Image id={self.id} sop={self.sop_instance_uid}>"
