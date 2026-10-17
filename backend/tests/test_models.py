"""ORM model tests — CRUD and relationship verification."""
import uuid
from datetime import date

import pytest

from app.models.patient import Patient
from app.models.study import Study
from app.models.series import Series
from app.models.image import Image
from app.models.analysis import Analysis
from app.models.embedding import Embedding
from app.core.config import settings
from tests.conftest import requires_db


# ── Helpers ─────────────────────────────────────────────────────────


def _make_patient(db, ext_id: str = "TEST-PT-001") -> Patient:
    p = Patient(external_patient_id=ext_id)
    db.add(p)
    db.flush()
    return p


def _make_study(db, patient: Patient, uid: str = "1.2.3.STUDY.001") -> Study:
    s = Study(patient_id=patient.id, study_uid=uid, modality="MR")
    db.add(s)
    db.flush()
    return s


def _make_series(db, study: Study, uid: str = "1.2.3.SERIES.001") -> Series:
    sr = Series(study_id=study.id, series_uid=uid, series_number=1, body_part="BRAIN")
    db.add(sr)
    db.flush()
    return sr


def _make_image(
    db, series: Series, sop_uid: str = "1.2.3.SOP.001"
) -> Image:
    img = Image(
        series_id=series.id,
        sop_instance_uid=sop_uid,
        file_path="/tmp/test.dcm",
        file_format="DICOM",
        slice_index=1,
        width=256,
        height=256,
    )
    db.add(img)
    db.flush()
    return img


# ── Patient ─────────────────────────────────────────────────────────


@requires_db
class TestPatientModel:
    def test_create_and_read(self, db_session):
        patient = _make_patient(db_session)
        assert patient.id is not None
        assert isinstance(patient.id, uuid.UUID)
        assert patient.external_patient_id == "TEST-PT-001"
        assert patient.created_at is not None

    def test_unique_external_id(self, db_session):
        _make_patient(db_session, "UNIQUE-001")
        with pytest.raises(Exception):
            _make_patient(db_session, "UNIQUE-001")
            db_session.flush()


# ── Study ───────────────────────────────────────────────────────────


@requires_db
class TestStudyModel:
    def test_create_with_patient_relationship(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        assert study.patient_id == patient.id
        assert study.study_uid == "1.2.3.STUDY.001"

    def test_patient_has_studies(self, db_session):
        patient = _make_patient(db_session)
        _make_study(db_session, patient, "1.2.3.S1")
        _make_study(db_session, patient, "1.2.3.S2")
        db_session.refresh(patient)
        assert len(patient.studies) == 2


# ── Series ──────────────────────────────────────────────────────────


@requires_db
class TestSeriesModel:
    def test_create_with_study_relationship(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        series = _make_series(db_session, study)
        assert series.study_id == study.id
        assert series.body_part == "BRAIN"

    def test_study_has_series(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        _make_series(db_session, study, "1.2.3.SR1")
        _make_series(db_session, study, "1.2.3.SR2")
        db_session.refresh(study)
        assert len(study.series) == 2


# ── Image ───────────────────────────────────────────────────────────


@requires_db
class TestImageModel:
    def test_create_with_series_relationship(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        series = _make_series(db_session, study)
        image = _make_image(db_session, series)
        assert image.series_id == series.id
        assert image.file_format == "DICOM"
        assert image.width == 256

    def test_series_has_images(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        series = _make_series(db_session, study)
        _make_image(db_session, series, "1.2.3.SOP.A")
        _make_image(db_session, series, "1.2.3.SOP.B")
        db_session.refresh(series)
        assert len(series.images) == 2


# ── Analysis ────────────────────────────────────────────────────────


@requires_db
class TestAnalysisModel:
    def test_create_with_json_result(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        analysis = Analysis(
            study_id=study.id,
            analysis_type="abnormality_detection",
            model_name="test-model",
            model_version="1.0",
            status="completed",
            result={"findings": [{"label": "tumor", "score": 0.95}]},
            confidence=0.95,
        )
        db_session.add(analysis)
        db_session.flush()
        assert analysis.id is not None
        assert analysis.result["findings"][0]["label"] == "tumor"
        assert analysis.status == "completed"

    def test_default_status_is_pending(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        analysis = Analysis(
            study_id=study.id,
            analysis_type="enhancement_quality",
            model_name="test-model",
        )
        db_session.add(analysis)
        db_session.flush()
        assert analysis.status == "pending"


# ── Embedding ───────────────────────────────────────────────────────


@requires_db
class TestEmbeddingModel:
    def test_vector_insert_and_retrieve(self, db_session):
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        dim = settings.EMBEDDING_DIMENSION
        vec = [float(i) / dim for i in range(dim)]
        emb = Embedding(
            study_id=study.id,
            embedding_type="image_feature",
            model_name="test-encoder",
            embedding=vec,
        )
        db_session.add(emb)
        db_session.flush()
        assert emb.id is not None

        # Re-query to verify persistence
        fetched = db_session.get(Embedding, emb.id)
        assert fetched is not None
        # pgvector returns a list/array; check first element
        assert abs(fetched.embedding[0] - 0.0) < 1e-5

    def test_vector_similarity_search(self, db_session):
        """Insert two embeddings and verify nearest-neighbour ordering."""
        patient = _make_patient(db_session)
        study = _make_study(db_session, patient)
        dim = settings.EMBEDDING_DIMENSION

        vec_a = [1.0] * dim
        vec_b = [0.0] * dim
        query = [0.9] * dim  # closer to vec_a

        for i, vec in enumerate([vec_a, vec_b]):
            db_session.add(
                Embedding(
                    study_id=study.id,
                    embedding_type="image_feature",
                    model_name="test-encoder",
                    embedding=vec,
                )
            )
        db_session.flush()

        from app.repositories.embedding import EmbeddingRepository

        repo = EmbeddingRepository(db_session)
        results = repo.similarity_search(query, limit=2)
        assert len(results) == 2
        # First result should be the one closer to the query
        closest_emb, closest_dist = results[0]
        furthest_emb, furthest_dist = results[1]
        assert closest_dist < furthest_dist
