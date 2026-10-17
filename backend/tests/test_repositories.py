"""Repository layer tests."""
import uuid
from datetime import date

import pytest

from app.models.patient import Patient
from app.models.study import Study
from app.models.series import Series
from app.models.image import Image
from app.repositories.patient import PatientRepository
from app.repositories.study import StudyRepository
from app.repositories.image import ImageRepository
from app.repositories.analysis import AnalysisRepository
from app.repositories.embedding import EmbeddingRepository
from app.core.config import settings
from tests.conftest import requires_db


# ── Helpers ─────────────────────────────────────────────────────────


def _seed_patient(db, ext_id="REPO-PT-001"):
    p = Patient(external_patient_id=ext_id)
    db.add(p)
    db.flush()
    return p


def _seed_study(db, patient, uid="1.2.REPO.STUDY"):
    s = Study(patient_id=patient.id, study_uid=uid, modality="MR")
    db.add(s)
    db.flush()
    return s


def _seed_series(db, study, uid="1.2.REPO.SERIES"):
    sr = Series(study_id=study.id, series_uid=uid, series_number=1)
    db.add(sr)
    db.flush()
    return sr


# ── PatientRepository ──────────────────────────────────────────────


@requires_db
class TestPatientRepository:
    def test_create_and_get_by_id(self, db_session):
        repo = PatientRepository(db_session)
        patient = repo.create(external_patient_id="REPO-001")
        fetched = repo.get_by_id(patient.id)
        assert fetched is not None
        assert fetched.external_patient_id == "REPO-001"

    def test_get_by_external_id(self, db_session):
        repo = PatientRepository(db_session)
        repo.create(external_patient_id="EXT-LOOKUP")
        result = repo.get_by_external_id("EXT-LOOKUP")
        assert result is not None

    def test_list(self, db_session):
        repo = PatientRepository(db_session)
        repo.create(external_patient_id="LIST-A")
        repo.create(external_patient_id="LIST-B")
        patients = repo.list()
        assert len(patients) >= 2

    def test_update(self, db_session):
        repo = PatientRepository(db_session)
        patient = repo.create(external_patient_id="UPD-BEFORE")
        updated = repo.update(patient.id, external_patient_id="UPD-AFTER")
        assert updated is not None
        assert updated.external_patient_id == "UPD-AFTER"

    def test_delete(self, db_session):
        repo = PatientRepository(db_session)
        patient = repo.create(external_patient_id="DEL-ME")
        assert repo.delete(patient.id) is True
        assert repo.get_by_id(patient.id) is None

    def test_delete_nonexistent(self, db_session):
        repo = PatientRepository(db_session)
        assert repo.delete(uuid.uuid4()) is False


# ── StudyRepository ────────────────────────────────────────────────


@requires_db
class TestStudyRepository:
    def test_create_and_get_by_uid(self, db_session):
        patient = _seed_patient(db_session, "STUDY-REPO-PT")
        repo = StudyRepository(db_session)
        study = repo.create(patient_id=patient.id, study_uid="1.2.3.UID")
        assert repo.get_by_uid("1.2.3.UID") is not None

    def test_list_by_patient(self, db_session):
        patient = _seed_patient(db_session, "LIST-PT")
        repo = StudyRepository(db_session)
        repo.create(patient_id=patient.id, study_uid="1.2.A")
        repo.create(patient_id=patient.id, study_uid="1.2.B")
        studies = repo.list_by_patient(patient.id)
        assert len(studies) == 2


# ── ImageRepository ────────────────────────────────────────────────


@requires_db
class TestImageRepository:
    def test_create_and_list_by_series(self, db_session):
        patient = _seed_patient(db_session, "IMG-REPO-PT")
        study = _seed_study(db_session, patient, "1.2.IMG.STUDY")
        series = _seed_series(db_session, study, "1.2.IMG.SERIES")
        repo = ImageRepository(db_session)
        repo.create(
            series_id=series.id,
            sop_instance_uid="1.2.3.SOP.R1",
            file_path="/test/img1.dcm",
        )
        repo.create(
            series_id=series.id,
            sop_instance_uid="1.2.3.SOP.R2",
            file_path="/test/img2.dcm",
        )
        images = repo.list_by_series(series.id)
        assert len(images) == 2


# ── AnalysisRepository ─────────────────────────────────────────────


@requires_db
class TestAnalysisRepository:
    def test_create_and_update_status(self, db_session):
        patient = _seed_patient(db_session, "ANA-REPO-PT")
        study = _seed_study(db_session, patient, "1.2.ANA.STUDY")
        repo = AnalysisRepository(db_session)
        analysis = repo.create(
            study_id=study.id,
            analysis_type="abnormality_detection",
            model_name="v1",
        )
        assert analysis.status == "pending"

        updated = repo.update_status(
            analysis.id,
            "completed",
            result={"ok": True},
            confidence=0.88,
        )
        assert updated is not None
        assert updated.status == "completed"
        assert updated.confidence == pytest.approx(0.88)
        assert updated.completed_at is not None

    def test_list_by_study(self, db_session):
        patient = _seed_patient(db_session, "ANA-LIST-PT")
        study = _seed_study(db_session, patient, "1.2.ANA.LIST")
        repo = AnalysisRepository(db_session)
        repo.create(study_id=study.id, analysis_type="t1", model_name="m")
        repo.create(study_id=study.id, analysis_type="t2", model_name="m")
        assert len(repo.list_by_study(study.id)) == 2


# ── EmbeddingRepository ────────────────────────────────────────────


@requires_db
class TestEmbeddingRepository:
    def test_create_and_list_by_study(self, db_session):
        patient = _seed_patient(db_session, "EMB-REPO-PT")
        study = _seed_study(db_session, patient, "1.2.EMB.STUDY")
        dim = settings.EMBEDDING_DIMENSION
        repo = EmbeddingRepository(db_session)
        repo.create(
            study_id=study.id,
            embedding_type="image_feature",
            model_name="test",
            embedding=[0.0] * dim,
        )
        results = repo.list_by_study(study.id)
        assert len(results) == 1

    def test_similarity_search_filtered_by_type(self, db_session):
        patient = _seed_patient(db_session, "EMB-FILTER-PT")
        study = _seed_study(db_session, patient, "1.2.EMB.FILT")
        dim = settings.EMBEDDING_DIMENSION
        repo = EmbeddingRepository(db_session)
        repo.create(
            study_id=study.id,
            embedding_type="image_feature",
            model_name="test",
            embedding=[1.0] * dim,
        )
        repo.create(
            study_id=study.id,
            embedding_type="report_text",
            model_name="test",
            embedding=[1.0] * dim,
        )
        results = repo.similarity_search(
            [1.0] * dim, embedding_type="report_text", limit=10,
        )
        assert all(e.embedding_type == "report_text" for e, _ in results)
