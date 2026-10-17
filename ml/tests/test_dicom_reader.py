"""Unit tests for DICOM reader module."""

from pathlib import Path
import pytest
import numpy as np

from ml.preprocessing.dicom_reader import DICOMReader, DICOMMetadata
from ml.scripts.generate_synthetic_data import create_synthetic_dicom_file


@pytest.fixture
def synthetic_dicom_path(tmp_path: Path) -> Path:
    """Create a temporary synthetic DICOM file for testing."""
    dcm_path = tmp_path / "test_slice.dcm"
    create_synthetic_dicom_file(
        output_path=dcm_path,
        patient_id="TEST-PATIENT-123",
        patient_name="DOE^TEST",
        study_uid="1.2.3.4.5",
        series_uid="1.2.3.4.5.6",
        sop_uid="1.2.3.4.5.6.7",
        instance_number=5,
        slice_location=15.0,
    )
    return dcm_path


def test_dicom_reader_nonexistent_file():
    """Verify FileNotFoundError raised for non-existent path."""
    with pytest.raises(FileNotFoundError):
        DICOMReader("non_existent_file.dcm")


def test_dicom_reader_extract_metadata(synthetic_dicom_path: Path):
    """Test DICOM metadata extraction into Pydantic schema."""
    reader = DICOMReader(synthetic_dicom_path)
    meta = reader.extract_metadata()

    assert isinstance(meta, DICOMMetadata)
    assert meta.patient_id == "TEST-PATIENT-123"
    assert meta.patient_name == "DOE^TEST"
    assert meta.study_instance_uid == "1.2.3.4.5"
    assert meta.series_instance_uid == "1.2.3.4.5.6"
    assert meta.sop_instance_uid == "1.2.3.4.5.6.7"
    assert meta.instance_number == 5
    assert meta.slice_location == 15.0
    assert meta.modality == "MR"
    assert meta.rows == 128
    assert meta.columns == 128


def test_dicom_reader_pixel_array(synthetic_dicom_path: Path):
    """Test pixel array extraction and rescale slope/intercept application."""
    reader = DICOMReader(synthetic_dicom_path)
    pixels = reader.get_pixel_array(apply_rescale=True)

    assert isinstance(pixels, np.ndarray)
    assert pixels.shape == (128, 128)
    assert pixels.dtype == np.float32
    assert np.max(pixels) > 0


def test_dicom_reader_normalized_image(synthetic_dicom_path: Path):
    """Test normalized 8-bit image array generation."""
    reader = DICOMReader(synthetic_dicom_path)
    img_8bit = reader.get_normalized_image(output_8bit=True)

    assert img_8bit.shape == (128, 128)
    assert img_8bit.dtype == np.uint8
    assert img_8bit.min() >= 0
    assert img_8bit.max() <= 255
