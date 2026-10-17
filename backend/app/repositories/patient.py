"""Patient repository — CRUD operations for Patient entities."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepository:
    """Data-access methods for the ``patients`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────
    def create(self, *, external_patient_id: str) -> Patient:
        """Insert a new patient record."""
        patient = Patient(external_patient_id=external_patient_id)
        self.db.add(patient)
        self.db.flush()
        return patient

    # ── Read ──────────────────────────────────────────────────────
    def get_by_id(self, patient_id: uuid.UUID) -> Optional[Patient]:
        """Return a patient by primary key, or ``None``."""
        return self.db.get(Patient, patient_id)

    def get_by_external_id(self, external_id: str) -> Optional[Patient]:
        """Look up a patient by their upstream external identifier."""
        stmt = select(Patient).where(Patient.external_patient_id == external_id)
        return self.db.execute(stmt).scalars().first()

    def list(self, *, offset: int = 0, limit: int = 100) -> List[Patient]:
        """Return a paginated list of patients."""
        stmt = select(Patient).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    # ── Update ────────────────────────────────────────────────────
    def update(self, patient_id: uuid.UUID, **fields) -> Optional[Patient]:
        """Update mutable fields on an existing patient."""
        patient = self.get_by_id(patient_id)
        if patient is None:
            return None
        for key, value in fields.items():
            if hasattr(patient, key):
                setattr(patient, key, value)
        self.db.flush()
        return patient

    # ── Delete ────────────────────────────────────────────────────
    def delete(self, patient_id: uuid.UUID) -> bool:
        """Delete a patient by id.  Returns ``True`` if deleted."""
        patient = self.get_by_id(patient_id)
        if patient is None:
            return False
        self.db.delete(patient)
        self.db.flush()
        return True
