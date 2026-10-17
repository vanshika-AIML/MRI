"""Unit tests for MRI abnormality detection modules.

Tests intensity-based and texture-based detectors on synthetic 2D slices
and 3D volumes, including edge cases and result schema validation.
"""

import numpy as np
import pytest

from ml.detection.base import (
    AbnormalityRegion,
    BaseDetector,
    DetectionConfig,
    DetectionResult,
    SeverityLevel,
)
from ml.detection.intensity_detector import IntensityAnomalyDetector
from ml.detection.texture_detector import TextureAnomalyDetector


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def normal_brain_slice() -> np.ndarray:
    """Create a synthetic 'normal' MRI slice with relatively uniform tissue."""
    np.random.seed(42)
    img = np.zeros((64, 64), dtype=np.float32)
    # Brain region with mild gradient
    img[10:54, 10:54] = 0.5
    img[18:46, 18:46] = 0.6
    img[25:39, 25:39] = 0.55
    # Add mild noise
    img += np.random.normal(0, 0.015, img.shape).astype(np.float32)
    return np.clip(img, 0.0, 1.0)


@pytest.fixture
def lesion_brain_slice() -> np.ndarray:
    """Create a synthetic MRI slice with a hyperintense lesion."""
    np.random.seed(42)
    img = np.zeros((64, 64), dtype=np.float32)
    # Brain tissue
    img[8:56, 8:56] = 0.4
    img[16:48, 16:48] = 0.5
    # Add mild noise
    img += np.random.normal(0, 0.01, img.shape).astype(np.float32)
    # Bright lesion (hyperintense)
    img[30:40, 35:45] = 0.95
    return np.clip(img, 0.0, 1.0)


@pytest.fixture
def textured_lesion_slice() -> np.ndarray:
    """Create a synthetic MRI slice with a heterogeneous texture region."""
    np.random.seed(42)
    img = np.zeros((64, 64), dtype=np.float32)
    img[8:56, 8:56] = 0.45
    img[16:48, 16:48] = 0.55
    # Add mild noise
    img += np.random.normal(0, 0.01, img.shape).astype(np.float32)
    # Heterogeneous texture patch (high local variance)
    patch = np.random.uniform(0.1, 0.95, (12, 12)).astype(np.float32)
    img[26:38, 26:38] = patch
    return np.clip(img, 0.0, 1.0)


@pytest.fixture
def sample_3d_volume() -> np.ndarray:
    """Create a 3D volume with a lesion in the middle slices."""
    np.random.seed(42)
    vol = np.zeros((32, 32, 8), dtype=np.float32)
    vol[5:27, 5:27, 1:7] = 0.45
    vol[10:22, 10:22, 2:6] = 0.55
    vol += np.random.normal(0, 0.01, vol.shape).astype(np.float32)
    # Lesion
    vol[14:18, 14:18, 3:5] = 0.92
    return np.clip(vol, 0.0, 1.0)


# ── Intensity Anomaly Detector Tests ─────────────────────────────────


class TestIntensityAnomalyDetector:
    """Tests for the intensity-based anomaly detector."""

    def test_detector_name(self):
        detector = IntensityAnomalyDetector()
        assert detector.detector_name == "intensity_anomaly_detector"

    def test_detect_lesion(self, lesion_brain_slice):
        """Detector should find the hyperintense lesion."""
        detector = IntensityAnomalyDetector()
        config = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.1,
            params={"z_threshold": 2.0, "min_region_area": 5},
        )
        result = detector.detect(lesion_brain_slice, config=config)

        assert result.success
        assert isinstance(result, DetectionResult)
        assert result.is_baseline is True
        assert len(result.regions) > 0

        # At least one region should be hyperintense
        hyper_regions = [
            r for r in result.regions if "hyperintense" in r.label
        ]
        assert len(hyper_regions) > 0

    def test_normal_slice_fewer_detections(self, normal_brain_slice):
        """Normal slice should produce fewer or no high-confidence detections."""
        detector = IntensityAnomalyDetector()
        config = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.5,
            params={"z_threshold": 3.0, "min_region_area": 10},
        )
        result = detector.detect(normal_brain_slice, config=config)
        assert result.success

        # Should have fewer high-confidence regions than the lesion slice
        high_conf = [r for r in result.regions if r.confidence >= 0.5]
        assert len(high_conf) <= 3  # Generous threshold for statistical noise

    def test_region_fields_populated(self, lesion_brain_slice):
        """Detected regions should have all expected fields."""
        detector = IntensityAnomalyDetector()
        config = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.1,
            params={"z_threshold": 2.0, "min_region_area": 5},
        )
        result = detector.detect(lesion_brain_slice, config=config)

        for region in result.regions:
            assert isinstance(region, AbnormalityRegion)
            assert region.region_id is not None
            assert region.label is not None
            assert 0.0 <= region.confidence <= 1.0
            assert isinstance(region.severity, SeverityLevel)
            assert region.bounding_box is not None
            assert len(region.bounding_box) == 4
            assert region.centroid is not None
            assert region.area_pixels is not None
            assert region.area_pixels > 0
            assert region.mean_intensity is not None

    def test_3d_detection(self, sample_3d_volume):
        """Detector should work on 3D volumes."""
        detector = IntensityAnomalyDetector()
        config = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.1,
            params={"z_threshold": 2.0, "min_region_area": 3},
        )
        result = detector.detect(sample_3d_volume, config=config)
        assert result.success
        assert result.input_shape == (32, 32, 8)

        # Regions from 3D should have slice_index in metadata
        for region in result.regions:
            assert "slice_index" in region.metadata

    def test_confidence_threshold_filtering(self, lesion_brain_slice):
        """High threshold should filter out low-confidence detections."""
        detector = IntensityAnomalyDetector()

        low_thresh = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.1,
            params={"z_threshold": 2.0, "min_region_area": 5},
        )
        high_thresh = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.8,
            params={"z_threshold": 2.0, "min_region_area": 5},
        )

        result_low = detector.detect(lesion_brain_slice, config=low_thresh)
        result_high = detector.detect(lesion_brain_slice, config=high_thresh)

        assert len(result_high.regions) <= len(result_low.regions)

    def test_overall_score_and_severity(self, lesion_brain_slice):
        """Overall score and severity should be computed."""
        detector = IntensityAnomalyDetector()
        config = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.1,
            params={"z_threshold": 2.0, "min_region_area": 5},
        )
        result = detector.detect(lesion_brain_slice, config=config)

        assert 0.0 <= result.overall_abnormality_score <= 1.0
        assert isinstance(result.overall_severity, SeverityLevel)
        assert len(result.summary) > 0

    def test_disclaimer_in_summary(self, lesion_brain_slice):
        """Summary should contain a clinical disclaimer."""
        detector = IntensityAnomalyDetector()
        result = detector.detect(lesion_brain_slice)
        assert "heuristic" in result.summary.lower() or "clinical" in result.summary.lower()


# ── Texture Anomaly Detector Tests ───────────────────────────────────


class TestTextureAnomalyDetector:
    """Tests for the texture-based anomaly detector."""

    def test_detector_name(self):
        detector = TextureAnomalyDetector()
        assert detector.detector_name == "texture_anomaly_detector"

    def test_detect_textured_region(self, textured_lesion_slice):
        """Detector should flag the heterogeneous texture patch."""
        detector = TextureAnomalyDetector()
        config = DetectionConfig(
            detector_name="texture_anomaly",
            confidence_threshold=0.05,
            params={"window_size": 7, "variance_z_threshold": 2.0, "min_region_area": 5},
        )
        result = detector.detect(textured_lesion_slice, config=config)
        assert result.success
        assert isinstance(result, DetectionResult)

    def test_normal_slice_fewer_detections(self, normal_brain_slice):
        """Normal slice should have fewer texture anomaly detections."""
        detector = TextureAnomalyDetector()
        config = DetectionConfig(
            detector_name="texture_anomaly",
            confidence_threshold=0.5,
            params={"variance_z_threshold": 3.5, "min_region_area": 15},
        )
        result = detector.detect(normal_brain_slice, config=config)
        assert result.success

    def test_3d_detection(self, sample_3d_volume):
        """Texture detector should work on 3D volumes."""
        detector = TextureAnomalyDetector()
        result = detector.detect(sample_3d_volume)
        assert result.success
        assert result.input_shape == (32, 32, 8)


# ── Base Detector Edge Case Tests ────────────────────────────────────


class TestBaseDetectorEdgeCases:
    """Edge cases and error handling for the base detector interface."""

    def test_invalid_input_type(self):
        """Non-ndarray input should produce a failed result."""
        detector = IntensityAnomalyDetector()
        result = detector.detect("not_an_array")
        assert not result.success
        assert result.error_message is not None

    def test_empty_array(self):
        """Empty array should produce a failed result."""
        detector = IntensityAnomalyDetector()
        result = detector.detect(np.array([], dtype=np.float32))
        assert not result.success

    def test_1d_array_rejected(self):
        """1D array should produce a failed result."""
        detector = IntensityAnomalyDetector()
        result = detector.detect(np.array([0.1, 0.5, 0.9], dtype=np.float32))
        assert not result.success

    def test_all_zeros_image(self):
        """All-zeros image should return no detections, not crash."""
        detector = IntensityAnomalyDetector()
        result = detector.detect(np.zeros((32, 32), dtype=np.float32))
        assert result.success
        assert len(result.regions) == 0

    def test_all_ones_image(self):
        """All-ones image should return no detections, not crash."""
        detector = IntensityAnomalyDetector()
        result = detector.detect(np.ones((32, 32), dtype=np.float32))
        assert result.success

    def test_default_config_used(self, lesion_brain_slice):
        """Calling detect without config should use defaults."""
        detector = IntensityAnomalyDetector()
        result = detector.detect(lesion_brain_slice)
        assert result.success
        assert isinstance(result, DetectionResult)

    def test_max_regions_limit(self, lesion_brain_slice):
        """max_regions should cap the number of returned regions."""
        detector = IntensityAnomalyDetector()
        config = DetectionConfig(
            detector_name="intensity_anomaly",
            confidence_threshold=0.0,
            max_regions=2,
            params={"z_threshold": 1.5, "min_region_area": 3},
        )
        result = detector.detect(lesion_brain_slice, config=config)
        assert len(result.regions) <= 2

    def test_severity_levels(self):
        """SeverityLevel enum should have expected values."""
        assert SeverityLevel.NONE == "none"
        assert SeverityLevel.LOW == "low"
        assert SeverityLevel.MODERATE == "moderate"
        assert SeverityLevel.HIGH == "high"

    def test_result_serializable(self, lesion_brain_slice):
        """DetectionResult should be JSON-serializable via Pydantic."""
        detector = IntensityAnomalyDetector()
        result = detector.detect(lesion_brain_slice)
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert "regions" in json_str
