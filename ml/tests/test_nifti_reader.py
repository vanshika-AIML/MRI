"""Unit tests for NIfTI reader module."""

from pathlib import Path
import pytest
import numpy as np

from ml.preprocessing.nifti_reader import NIfTIReader, NIfTIMetadata
from ml.scripts.generate_synthetic_data import create_synthetic_nifti_file


@pytest.fixture
def synthetic_nifti_path(tmp_path: Path) -> Path:
    """Create a temporary synthetic 3D NIfTI file."""
    nifti_path = tmp_path / "brain_test.nii.gz"
    create_synthetic_nifti_file(nifti_path, shape=(32, 32, 16), add_lesion=True)
    return nifti_path


def test_nifti_reader_nonexistent_file():
    """Verify FileNotFoundError raised for non-existent path."""
    with pytest.raises(FileNotFoundError):
        NIfTIReader("non_existent_volume.nii.gz")


def test_nifti_reader_extract_metadata(synthetic_nifti_path: Path):
    """Test NIfTI spatial and affine metadata extraction."""
    reader = NIfTIReader(synthetic_nifti_path)
    meta = reader.extract_metadata()

    assert isinstance(meta, NIfTIMetadata)
    assert meta.dimensions == (32, 32, 16)
    assert len(meta.voxel_spacing) >= 3
    assert len(meta.affine) == 4
    assert meta.affine[3] == [0.0, 0.0, 0.0, 1.0]


def test_nifti_reader_get_fdata(synthetic_nifti_path: Path):
    """Test 3D volume array extraction."""
    reader = NIfTIReader(synthetic_nifti_path)
    vol = reader.get_fdata()

    assert isinstance(vol, np.ndarray)
    assert vol.shape == (32, 32, 16)
    assert vol.dtype == np.float32


def test_nifti_reader_slicing(synthetic_nifti_path: Path):
    """Test axial, sagittal, and coronal slice extraction."""
    reader = NIfTIReader(synthetic_nifti_path)

    axial_slice = reader.get_slice(8, plane="axial")
    sagittal_slice = reader.get_slice(16, plane="sagittal")
    coronal_slice = reader.get_slice(16, plane="coronal")

    assert axial_slice.ndim == 2
    assert sagittal_slice.ndim == 2
    assert coronal_slice.ndim == 2


def test_nifti_reader_middle_slices(synthetic_nifti_path: Path):
    """Test middle slice extraction for all 3 standard anatomical planes."""
    reader = NIfTIReader(synthetic_nifti_path)
    slices = reader.get_middle_slices()

    assert "axial" in slices
    assert "sagittal" in slices
    assert "coronal" in slices
    assert slices["axial"].ndim == 2
