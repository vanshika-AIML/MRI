"""Tests for the medical image IngestionService."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.ingestion import IngestionService
from ml.scripts.generate_synthetic_data import (
    create_synthetic_dicom_file,
    create_synthetic_nifti_file,
)
from ml.preprocessing.dicom_reader import DICOMReader
from ml.preprocessing.nifti_reader import NIfTIReader
from tests.conftest import requires_db


class TestIngestionServiceOffline:
    """Test ingestion parsing logic without requiring live PostgreSQL database connection."""

    def test_dicom_parsing_and_slice_rendering(self, tmp_path: Path):
        dcm_path = tmp_path / "offline_slice.dcm"
        create_synthetic_dicom_file(
            output_path=dcm_path,
            patient_id="OFFLINE-PAT-001",
            study_uid="1.2.3.4",
            series_uid="1.2.3.4.5",
            sop_uid="1.2.3.4.5.6",
        )

        reader = DICOMReader(dcm_path)
        meta = reader.extract_metadata()
        img_8bit = reader.get_normalized_image(output_8bit=True)

        assert meta.patient_id == "OFFLINE-PAT-001"
        assert meta.study_instance_uid == "1.2.3.4"
        assert img_8bit.shape == (128, 128)

    def test_nifti_parsing_and_slice_rendering(self, tmp_path: Path):
        nii_path = tmp_path / "offline_brain.nii.gz"
        create_synthetic_nifti_file(nii_path, shape=(32, 32, 16))

        reader = NIfTIReader(nii_path)
        meta = reader.extract_metadata()
        slices = reader.get_middle_slices()

        assert meta.dimensions == (32, 32, 16)
        assert "axial" in slices
        assert "sagittal" in slices
        assert "coronal" in slices


@requires_db
class TestIngestionServiceWithDB:
    """Test IngestionService with real DB transactions."""

    def test_process_dicom_file(self, db_session, tmp_path: Path):
        dcm_path = tmp_path / "slice_01.dcm"
        create_synthetic_dicom_file(
            output_path=dcm_path,
            patient_id="INGEST-PAT-001",
            study_uid="1.2.840.9999.1",
            series_uid="1.2.840.9999.2",
            sop_uid="1.2.840.9999.3",
        )

        service = IngestionService(db=db_session, storage_dir=tmp_path / "storage")
        image_record = service.process_dicom_file(dcm_path)

        assert image_record is not None
        assert image_record.sop_instance_uid == "1.2.840.9999.3"
        assert Path(image_record.file_path).exists()

    def test_process_nifti_volume(self, db_session, tmp_path: Path):
        nii_path = tmp_path / "brain_3d.nii.gz"
        create_synthetic_nifti_file(nii_path, shape=(32, 32, 16))

        service = IngestionService(db=db_session, storage_dir=tmp_path / "storage")
        images = service.process_nifti_volume(nii_path, patient_ext_id="NIFTI-PAT-001")

        assert len(images) == 3  # axial, sagittal, coronal
        for img in images:
            assert Path(img.file_path).exists()
