"""Owned analysis snapshots, independent of optional clinical study linkage."""
import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
