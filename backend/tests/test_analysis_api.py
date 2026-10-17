"""Automated test suite for Phase 6 MRI AI Inference API & AnalysisService."""

import io
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image as PILImage
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_current_user_optional, get_db_optional
from app.schemas.analysis import CLINICAL_DISCLAIMER, AnalysisResponse
from app.services.analysis import AnalysisService
from ml.scripts.generate_synthetic_data import create_synthetic_dicom_file, create_synthetic_nifti_file

client = TestClient(app)


@pytest.fixture(autouse=True)
def authenticated_viewer_without_database():
    app.dependency_overrides[get_current_user_optional] = lambda: {
        "sub": "a5d8f14c-e7a1-44af-9d56-0882c755dc44",
        "role": "viewer",
    }
    app.dependency_overrides[get_db_optional] = lambda: None
    yield
    app.dependency_overrides.pop(get_current_user_optional, None)
    app.dependency_overrides.pop(get_db_optional, None)


def test_multiframe_dicom_uses_last_axis_and_checks_size(tmp_path):
    import pydicom

    path = create_synthetic_dicom_file(tmp_path / "frames.dcm", pixel_array=np.ones((8, 10), dtype=np.uint16))
    dataset = pydicom.dcmread(path)
    dataset.NumberOfFrames = 3
    dataset.PixelData = np.stack([np.full((8, 10), i, dtype=np.uint16) for i in range(3)]).tobytes()
    dataset.save_as(path, enforce_file_format=True)
    array, _ = AnalysisService().parse_and_validate_file(path.read_bytes(), "frames.dcm")
    assert array.shape == (8, 10, 3)
    assert array[0, 0, 2] > array[0, 0, 0]
    dataset.NumberOfFrames = 1_000_000
    dataset.save_as(path, enforce_file_format=True)
    with pytest.raises(ValueError, match="DICOM"):
        AnalysisService().parse_and_validate_file(path.read_bytes(), "oversized.dcm")


def _create_synthetic_png_bytes(width: int = 64, height: int = 64) -> bytes:
    """Helper to create a synthetic grayscale PNG image with an anomaly spot."""
    arr = np.zeros((height, width), dtype=np.uint8) + 50
    # Add a bright anomaly spot in center
    arr[20:30, 20:30] = 240
    img = PILImage.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_synthetic_npy_bytes(shape: tuple = (32, 32, 8)) -> bytes:
    """Helper to create a synthetic numpy volume array as .npy bytes."""
    arr = np.zeros(shape, dtype=np.float32) + 0.1
    # Add anomaly blob in 3D center
    arr[10:20, 10:20, 2:6] = 0.95
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


# ==============================================================================
# 1. API Route Integration Tests
# ==============================================================================

def test_analysis_endpoint_2d_png():
    """Verify POST /api/v1/analysis with a valid 2D PNG file returns 200 OK and expected schema."""
    png_bytes = _create_synthetic_png_bytes()
    response = client.post(
        "/api/v1/analysis",
        files={"file": ("brain_slice.png", png_bytes, "image/png")},
        data={
            "normalize": "true",
            "normalization_method": "minmax",
            "enable_enhancement": "true",
            "enhancement_methods": "clahe",
            "enable_detection": "true",
            "detection_methods": "intensity_anomaly",
            "confidence_threshold": "0.2",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["success"] is True
    assert data["is_baseline"] is True
    assert data["model_name"] == "baseline_mri_pipeline"
    assert "analysis_id" in data
    assert data["clinical_disclaimer"] == CLINICAL_DISCLAIMER

    # Metadata
    meta = data["input_metadata"]
    assert meta["filename"] == "brain_slice.png"
    assert meta["source_format"] == "image"
    assert meta["ndim"] == 2
    assert meta["dimensions"] == [64, 64]

    # Stage results & regions
    assert len(data["stage_results"]) > 0
    assert "detected_regions" in data
    assert isinstance(data["detected_regions"], list)
    assert data["severity"] in (
        "not_assessed",
        "low",
        "medium",
        "moderate",
        "high",
    )
    if not data["detected_regions"]:
        assert data["severity"] == "not_assessed"
    assert 0.0 <= data["overall_confidence"] <= 1.0


def test_analysis_endpoint_3d_npy():
    """Verify POST /api/v1/analysis with a 3D numpy file returns 200 OK and preserves 3D shape."""
    npy_bytes = _create_synthetic_npy_bytes(shape=(32, 32, 6))
    response = client.post(
        "/api/v1/analysis",
        files={"file": ("mri_volume.npy", npy_bytes, "application/octet-stream")},
        data={"confidence_threshold": "0.3"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    meta = data["input_metadata"]
    assert meta["filename"] == "mri_volume.npy"
    assert meta["source_format"] == "numpy"
    assert meta["ndim"] == 3
    assert meta["dimensions"] == [32, 32, 6]


def test_analysis_endpoint_dicom(tmp_path: Path):
    """Verify POST /api/v1/analysis with a valid DICOM file."""
    dcm_file_path = tmp_path / "test_scan.dcm"
    create_synthetic_dicom_file(
        output_path=dcm_file_path,
        patient_id="PATIENT-DICOM-001",
    )
    dcm_bytes = dcm_file_path.read_bytes()

    response = client.post(
        "/api/v1/analysis",
        files={"file": ("test_scan.dcm", dcm_bytes, "application/dicom")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["input_metadata"]["source_format"] == "dicom"
    assert data["input_metadata"]["patient_id"] == "PATIENT-DICOM-001"


def test_analysis_endpoint_nifti(tmp_path: Path):
    """Verify POST /api/v1/analysis with a NIfTI file."""
    nii_file_path = tmp_path / "brain_3d.nii.gz"
    create_synthetic_nifti_file(
        output_path=nii_file_path,
        shape=(32, 32, 10),
    )
    nii_bytes = nii_file_path.read_bytes()

    response = client.post(
        "/api/v1/analysis",
        files={"file": ("brain_3d.nii.gz", nii_bytes, "application/octet-stream")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["input_metadata"]["source_format"] == "nifti"
    assert data["input_metadata"]["dimensions"] == [32, 32, 10]


# ==============================================================================
# 2. Validation & Security Error Edge Cases
# ==============================================================================

def test_analysis_endpoint_empty_file():
    """Verify empty 0-byte file returns 400 Bad Request."""
    response = client.post(
        "/api/v1/analysis",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["status_code"] == 400
    assert "empty" in data["error"]["message"].lower()


def test_analysis_endpoint_unsupported_format():
    """Verify unsupported file extension returns 400 Bad Request."""
    response = client.post(
        "/api/v1/analysis",
        files={"file": ("notes.txt", b"Invalid text file content", "text/plain")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "unsupported" in data["error"]["message"].lower() or "invalid" in data["error"]["message"].lower()


def test_analysis_endpoint_corrupt_file():
    """Verify corrupt image content returns 400 Bad Request."""
    response = client.post(
        "/api/v1/analysis",
        files={"file": ("corrupt.png", b"NOT_A_REAL_PNG_HEADER_12345", "image/png")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_analysis_endpoint_invalid_1d_array():
    """Verify 1D array numpy file is rejected with 400 Bad Request."""
    buf = io.BytesIO()
    np.save(buf, np.arange(100, dtype=np.float32))
    npy_1d_bytes = buf.getvalue()

    response = client.post(
        "/api/v1/analysis",
        files={"file": ("array_1d.npy", npy_1d_bytes, "application/octet-stream")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "dimension" in data["error"]["message"].lower()


def test_analysis_endpoint_with_auth_header():
    """Missing or invalid credentials must not silently become a guest request."""
    app.dependency_overrides.pop(get_current_user_optional, None)
    png_bytes = _create_synthetic_png_bytes()
    unauthenticated = client.post(
        "/api/v1/analysis",
        files={"file": ("scan.png", png_bytes, "image/png")},
    )
    assert unauthenticated.status_code == 401
    response = client.post(
        "/api/v1/analysis",
        files={"file": ("scan.png", png_bytes, "image/png")},
        headers={"Authorization": "Bearer test-api-key-12345"},
    )
    assert response.status_code == 401


def test_analysis_options_disabled_stages():
    """Verify stage toggling (disabling enhancement and detection)."""
    png_bytes = _create_synthetic_png_bytes()
    response = client.post(
        "/api/v1/analysis",
        files={"file": ("scan.png", png_bytes, "image/png")},
        data={
            "enable_enhancement": "false",
            "enable_detection": "false",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["detected_regions"]) == 0
    assert data["severity"] == "not_assessed"


def test_research_segmentation_requires_authentication_and_database():
    from app.api.dependencies import get_current_user_optional, get_db_optional

    app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        response = client.post(
            "/api/v1/analysis",
            files={"file": ("scan.nii.gz", b"not-parsed", "application/gzip")},
            data={
                "analysis_method": "research_flair_segmentation",
                "flair_sequence_confirmed": "true",
            },
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

    app.dependency_overrides[get_current_user_optional] = lambda: {"sub": "a5d8f14c-e7a1-44af-9d56-0882c755dc44", "role": "viewer"}
    app.dependency_overrides[get_db_optional] = lambda: None
    try:
        response = client.post(
            "/api/v1/analysis",
            files={"file": ("scan.nii.gz", b"not-parsed", "application/gzip")},
            data={
                "analysis_method": "research_flair_segmentation",
                "flair_sequence_confirmed": "true",
            },
        )
        assert response.status_code == 503
        assert "Database" in response.json()["error"]["message"]
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_db_optional, None)


def test_research_segmentation_persists_model_output_without_baseline_fallback(monkeypatch):
    import uuid
    from app.api.dependencies import get_current_user_optional, get_db_optional
    from app.api.routes import analysis as analysis_route

    class FakeDb:
        def __init__(self):
            self.added = []

        def add(self, item):
            self.added.append(item)

        def flush(self):
            pass

    class FakeSegmenter:
        def predict(self, content, filename):
            assert content == b"nifti payload"
            assert filename == "research_flair.nii.gz"
            return {
                "target": "whole_tumor_label_gt_0",
                "modality": "FLAIR",
                "mask_format": "application/gzip+nifti",
                "mask_nifti_gz_base64": "mask",
                "overlay_format": "image/png",
                "overlay_png_base64": "overlay",
                "preview_slice_index": 0,
                "mask_dimensions": [8, 8, 2],
                "affine": [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
                "voxel_spacing_mm": [1.0, 1.0, 1.0],
                "predicted_voxels": 5,
                "threshold": 0.5,
                "preprocessing_version": "flair-zscore-ras-v1",
                "checkpoint_sha256": "f" * 64,
                "input_sha256": "a" * 64,
                "mask_sha256": "b" * 64,
            }

    fake_db = FakeDb()
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user_optional] = lambda: {"sub": user_id, "role": "viewer"}
    app.dependency_overrides[get_db_optional] = lambda: fake_db
    monkeypatch.setattr(analysis_route, "get_tumor_segmenter", lambda: FakeSegmenter())
    monkeypatch.setattr(
        AnalysisService,
        "parse_and_validate_file",
        lambda *args, **kwargs: pytest.fail("Research mode must not call the baseline parser"),
    )
    try:
        response = client.post(
            "/api/v1/analysis",
            files={"file": ("scan.nii.gz", b"nifti payload", "application/gzip")},
            data={
                "analysis_method": "research_flair_segmentation",
                "flair_sequence_confirmed": "true",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_db_optional, None)

    assert response.status_code == 200
    result = response.json()
    assert result["is_baseline"] is False
    assert result["model_name"] == "msd_flair_whole_tumor_unet"
    assert result["input_metadata"]["filename"] == "research_flair.nii.gz"
    assert result["prediction"]["mask_sha256"] == "b" * 64
    assert len(fake_db.added) == 1
    assert fake_db.added[0].owner_id == uuid.UUID(user_id)
    assert fake_db.added[0].result["prediction"]["mask_sha256"] == "b" * 64


def test_research_segmentation_model_unavailable_does_not_fall_back(monkeypatch):
    from app.api.dependencies import get_current_user_optional, get_db_optional
    from app.api.routes import analysis as analysis_route

    class FakeDb:
        def add(self, item):
            pytest.fail("Unavailable model must not persist a heuristic result")

        def flush(self):
            pytest.fail("Unavailable model must not persist a heuristic result")

    app.dependency_overrides[get_current_user_optional] = lambda: {
        "sub": "a5d8f14c-e7a1-44af-9d56-0882c755dc44",
        "role": "viewer",
    }
    app.dependency_overrides[get_db_optional] = lambda: FakeDb()
    monkeypatch.setattr(
        analysis_route,
        "get_tumor_segmenter",
        lambda: (_ for _ in ()).throw(FileNotFoundError("model absent")),
    )
    monkeypatch.setattr(
        AnalysisService,
        "parse_and_validate_file",
        lambda *args, **kwargs: pytest.fail("Research mode must not fall back to the baseline parser"),
    )
    try:
        response = client.post(
            "/api/v1/analysis",
            files={"file": ("scan.nii.gz", b"nifti payload", "application/gzip")},
            data={
                "analysis_method": "research_flair_segmentation",
                "flair_sequence_confirmed": "true",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_db_optional, None)

    assert response.status_code == 503
    assert "not configured or available" in response.json()["error"]["message"]


def test_research_segmentation_endpoint_runs_real_checkpoint_and_saves_artifact(monkeypatch):
    import base64
    import gzip
    import uuid
    import nibabel as nib
    from app.api.dependencies import get_current_user_optional, get_db_optional
    from app.api.routes import analysis as analysis_route
    from ml.inference.tumor_segmenter import TumorSegmenter

    run_dir = Path(__file__).resolve().parents[2] / "ml" / "runs" / "msd-flair-pilot"
    if not (run_dir / "weights.pt").is_file():
        pytest.skip("Local pilot checkpoint is unavailable")

    class FakeDb:
        def __init__(self):
            self.added = []

        def add(self, item):
            self.added.append(item)

        def flush(self):
            pass

    volume = np.zeros((24, 20, 5), dtype=np.float32)
    volume[3:21, 2:18, 1:4] = 1
    affine = np.diag([1.5, 2.0, 2.5, 1.0])
    upload = gzip.compress(nib.Nifti1Image(volume, affine).to_bytes(), mtime=0)
    fake_db = FakeDb()
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user_optional] = lambda: {"sub": user_id, "role": "viewer"}
    app.dependency_overrides[get_db_optional] = lambda: fake_db
    monkeypatch.setattr(
        analysis_route,
        "get_tumor_segmenter",
        lambda: TumorSegmenter(run_dir),
    )
    try:
        response = client.post(
            "/api/v1/analysis",
            files={"file": ("subject-name.nii.gz", upload, "application/gzip")},
            data={
                "analysis_method": "research_flair_segmentation",
                "flair_sequence_confirmed": "true",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_db_optional, None)

    assert response.status_code == 200
    result = response.json()
    assert result["is_baseline"] is False
    assert result["input_metadata"]["filename"] == "research_flair.nii.gz"
    prediction = result["prediction"]
    mask = nib.Nifti1Image.from_bytes(
        gzip.decompress(base64.b64decode(prediction["mask_nifti_gz_base64"]))
    )
    assert mask.shape == (24, 20, 5)
    assert np.allclose(mask.affine, affine)
    assert prediction["predicted_voxels"] == int(np.asarray(mask.dataobj).sum())
    assert len(fake_db.added) == 1
    assert fake_db.added[0].owner_id == uuid.UUID(user_id)
    assert fake_db.added[0].result["prediction"]["mask_sha256"] == prediction["mask_sha256"]


# ==============================================================================
# 3. Unit Tests for AnalysisService
# ==============================================================================

def test_analysis_service_direct():
    """Direct unit testing of AnalysisService parsing and analysis execution."""
    service = AnalysisService(db=None)

    png_bytes = _create_synthetic_png_bytes(32, 32)
    arr, meta = service.parse_and_validate_file(png_bytes, "test.png")

    assert isinstance(arr, np.ndarray)
    assert arr.shape == (32, 32)
    assert meta["source_format"] == "image"

    res = service.run_analysis(arr, meta)
    assert isinstance(res, AnalysisResponse)
    assert res.success is True
    assert res.is_baseline is True
    assert res.clinical_disclaimer == CLINICAL_DISCLAIMER


def test_empty_baseline_output_is_not_reported_as_normal():
    service = AnalysisService(db=None)
    arr, metadata = service.parse_and_validate_file(
        _create_synthetic_npy_bytes(shape=(32, 32, 4)), "uniform.npy"
    )
    arr.fill(1.0)

    response = service.run_analysis(arr, metadata)

    assert response.success is True
    assert response.model_name == "baseline_mri_pipeline"
    assert response.detected_regions_count == 0
    assert response.severity == "not_assessed"
    assert "normal" not in response.summary.lower()
    assert any("cannot establish" in warning.lower() for warning in response.warnings)
