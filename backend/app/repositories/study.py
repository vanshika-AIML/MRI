"""Study repository — CRUD operations for Study entities."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.study import Study


class StudyRepository:
    """Data-access methods for the ``studies`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────
    def create(self, *, patient_id: uuid.UUID, study_uid: str, **kwargs) -> Study:
        """Insert a new study record."""
        study = Study(patient_id=patient_id, study_uid=study_uid, **kwargs)
        self.db.add(study)
        self.db.flush()
        return study

    # ── Read ──────────────────────────────────────────────────────
    def get_by_id(self, study_id: uuid.UUID) -> Optional[Study]:
        return self.db.get(Study, study_id)

    def get_by_uid(self, study_uid: str) -> Optional[Study]:
        stmt = select(Study).where(Study.study_uid == study_uid)
        return self.db.execute(stmt).scalars().first()

    def list_by_patient(
        self, patient_id: uuid.UUID, *, offset: int = 0, limit: int = 100,
    ) -> List[Study]:
        stmt = (
            select(Study)
            .where(Study.patient_id == patient_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    # ── Update ────────────────────────────────────────────────────
    def update(self, study_id: uuid.UUID, **fields) -> Optional[Study]:
        study = self.get_by_id(study_id)
        if study is None:
            return None
        for key, value in fields.items():
            if hasattr(study, key):
                setattr(study, key, value)
        self.db.flush()
        return study

    # ── Delete ────────────────────────────────────────────────────
    def delete(self, study_id: uuid.UUID) -> bool:
        study = self.get_by_id(study_id)
        if study is None:
            return False
        self.db.delete(study)
        self.db.flush()
        return True
