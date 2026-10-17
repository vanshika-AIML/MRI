"""Seed the development database with synthetic MRI data.

Usage:
    python -m app.db.seed

Safe to run repeatedly — checks for existing data before inserting.
All data is clearly synthetic and contains no real patient information.
"""
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.patient import Patient
from app.models.study import Study
from app.models.series import Series
from app.models.image import Image
from app.models.analysis import Analysis
from app.models.embedding import Embedding


SEED_EXTERNAL_ID = "SYNTH-PATIENT-001"


def seed() -> None:
    """Insert minimal synthetic development data."""
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL not configured — cannot seed.")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Guard: skip if seed data already exists
        existing = db.execute(
            select(Patient).where(Patient.external_patient_id == SEED_EXTERNAL_ID)
        ).scalars().first()
        if existing:
            logger.info("Seed data already present — skipping.")
            return

        # 1 Patient
        patient = Patient(external_patient_id=SEED_EXTERNAL_ID)
        db.add(patient)
        db.flush()

        # 1 Study
        study = Study(
            patient_id=patient.id,
            study_uid="1.2.840.10008.SYNTH.STUDY.001",
            modality="MR",
            description="Synthetic brain MRI study for development",
        )
        db.add(study)
        db.flush()

        # 1 Series
        series = Series(
            study_id=study.id,
            series_uid="1.2.840.10008.SYNTH.SERIES.001",
            series_number=1,
            description="T1-weighted axial",
            body_part="BRAIN",
        )
        db.add(series)
        db.flush()

        # 3 Images
        for i in range(1, 4):
            image = Image(
                series_id=series.id,
                sop_instance_uid=f"1.2.840.10008.SYNTH.SOP.{i:03d}",
                file_path=f"/data/synthetic/brain_slice_{i:03d}.dcm",
                file_format="DICOM",
                slice_index=i,
                width=256,
                height=256,
            )
            db.add(image)
        db.flush()

        # 1 Analysis
        analysis = Analysis(
            study_id=study.id,
            analysis_type="abnormality_detection",
            model_name="synthetic-detector",
            model_version="0.0.1-dev",
            status="completed",
            result={"findings": [], "note": "Synthetic — no real analysis performed"},
            confidence=0.0,
        )
        db.add(analysis)
        db.flush()

        # 1 Embedding (zero-vector of correct dimension)
        dim = settings.EMBEDDING_DIMENSION
        embedding = Embedding(
            study_id=study.id,
            embedding_type="image_feature",
            model_name="synthetic-encoder",
            model_version="0.0.1-dev",
            embedding=[0.0] * dim,
        )
        db.add(embedding)

        db.commit()
        logger.info("Development seed data inserted successfully.")

    except Exception:
        db.rollback()
        logger.error("Seed failed", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
