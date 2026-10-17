"""Embedding model — vector embeddings stored via pgvector."""
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base


class Embedding(Base):
    """A vector embedding generated from MRI data.

    Uses pgvector's ``vector`` type for similarity search via
    ``<->`` (L2), ``<=>`` (cosine), or ``<#>`` (inner-product) operators.

    The vector dimension is controlled by ``settings.EMBEDDING_DIMENSION``.
    """

    __tablename__ = "embeddings"

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

    embedding_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="e.g. image_feature, report_text",
    )

    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # pgvector column — dimension is configurable via settings.
    embedding = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────
    study = relationship("Study", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding id={self.id} type={self.embedding_type}>"
