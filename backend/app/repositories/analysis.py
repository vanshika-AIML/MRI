"""Analysis repository — CRUD operations for Analysis entities."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis


class AnalysisRepository:
    """Data-access methods for the ``analyses`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────
    def create(
        self,
        *,
        study_id: uuid.UUID,
        analysis_type: str,
        model_name: str,
        **kwargs,
    ) -> Analysis:
        analysis = Analysis(
            study_id=study_id,
            analysis_type=analysis_type,
            model_name=model_name,
            **kwargs,
        )
        self.db.add(analysis)
        self.db.flush()
        return analysis

    # ── Read ──────────────────────────────────────────────────────
    def get_by_id(self, analysis_id: uuid.UUID) -> Optional[Analysis]:
        return self.db.get(Analysis, analysis_id)

    def list_by_study(
        self, study_id: uuid.UUID, *, offset: int = 0, limit: int = 100,
    ) -> List[Analysis]:
        stmt = (
            select(Analysis)
            .where(Analysis.study_id == study_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    # ── Update ────────────────────────────────────────────────────
    def update_status(
        self,
        analysis_id: uuid.UUID,
        status: str,
        *,
        result: dict | None = None,
        confidence: float | None = None,
    ) -> Optional[Analysis]:
        """Transition the analysis to a new status, optionally setting results."""
        analysis = self.get_by_id(analysis_id)
        if analysis is None:
            return None
        analysis.status = status
        if result is not None:
            analysis.result = result
        if confidence is not None:
            analysis.confidence = confidence
        if status in ("completed", "failed"):
            analysis.completed_at = datetime.now(timezone.utc)
        self.db.flush()
        return analysis
