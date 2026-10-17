"""Unit tests for the MRI inference pipeline and model registry.

Tests the end-to-end pipeline (preprocessing → enhancement → detection → result),
model registry operations, schema validation, and edge cases.
"""

import numpy as np
import pytest

from ml.detection.base import DetectionResult, SeverityLevel
from ml.detection.intensity_detector import IntensityAnomalyDetector
from ml.detection.texture_detector import TextureAnomalyDetector
from ml.enhancement.base import EnhancementResult
from ml.enhancement.contrast import CLAHEEnhancer, HistogramEqualizationEnhancer
from ml.enhancement.denoise import GaussianDenoiser
from ml.enhancement.sharpening import UnsharpMaskEnhancer
from ml.inference.pipeline import MRIInferencePipeline
from ml.inference.schemas import (
    InferenceInput,
    InferenceOutput,
    PipelineStage,
    PipelineStageResult,
)
from ml.models.registry import ModelRegistry


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def default_registry() -> ModelRegistry:
    """Create a default model registry with all baseline models."""
    return ModelRegistry.create_default()


@pytest.fixture
def pipeline(default_registry) -> MRIInferencePipeline:
    """Create an inference pipeline with default registry."""
    return MRIInferencePipeline(registry=default_registry)


@pytest.fixture
def sample_2d_image() -> np.ndarray:
    """Synthetic 2D MRI slice with a lesion."""
    np.random.seed(42)
    img = np.zeros((64, 64), dtype=np.float32)
    img[8:56, 8:56] = 400.0
    img[16:48, 16:48] = 600.0
    img[30:40, 35:45] = 950.0  # Lesion
    img += np.random.normal(0, 5.0, img.shape).astype(np.float32)
    return np.maximum(img, 0.0)


@pytest.fixture
def sample_3d_volume() -> np.ndarray:
    """Synthetic 3D MRI volume with a lesion."""
    np.random.seed(42)
    vol = np.zeros((32, 32, 8), dtype=np.float32)
    vol[5:27, 5:27, 1:7] = 400.0
    vol[10:22, 10:22, 2:6] = 600.0
    vol[14:18, 14:18, 3:5] = 950.0  # Lesion
    vol += np.random.normal(0, 5.0, vol.shape).astype(np.float32)
    return np.maximum(vol, 0.0)


@pytest.fixture
def normalized_2d() -> np.ndarray:
    """Already-normalized 2D slice in [0, 1] range."""
    np.random.seed(42)
    img = np.zeros((64, 64), dtype=np.float32)
    img[8:56, 8:56] = 0.4
    img[16:48, 16:48] = 0.6
    img[30:40, 35:45] = 0.95
    img += np.random.normal(0, 0.01, img.shape).astype(np.float32)
    return np.clip(img, 0.0, 1.0)


# ── Model Registry Tests ────────────────────────────────────────────


class TestModelRegistry:
    """Tests for the model registry."""

    def test_create_default_registry(self, default_registry):
        """Default registry should contain all baseline models."""
        assert len(default_registry.list_enhancers()) == 5
        assert len(default_registry.list_detectors()) == 2

        assert "clahe" in default_registry.list_enhancers()
        assert "gaussian_denoise" in default_registry.list_enhancers()
        assert "intensity_anomaly" in default_registry.list_detectors()
        assert "texture_anomaly" in default_registry.list_detectors()

    def test_register_enhancer(self):
        registry = ModelRegistry()
        enhancer = CLAHEEnhancer()
        registry.register_enhancer("test_clahe", enhancer)

        assert "test_clahe" in registry.list_enhancers()
        assert registry.get_enhancer("test_clahe") is enhancer

    def test_register_detector(self):
        registry = ModelRegistry()
        detector = IntensityAnomalyDetector()
        registry.register_detector("test_detector", detector)

        assert "test_detector" in registry.list_detectors()
        assert registry.get_detector("test_detector") is detector

    def test_get_nonexistent_enhancer(self):
        registry = ModelRegistry()
        assert registry.get_enhancer("nonexistent") is None

    def test_get_nonexistent_detector(self):
        registry = ModelRegistry()
        assert registry.get_detector("nonexistent") is None

    def test_register_invalid_enhancer_type(self):
        registry = ModelRegistry()
        with pytest.raises(TypeError):
            registry.register_enhancer("bad", "not_an_enhancer")

    def test_register_invalid_detector_type(self):
        registry = ModelRegistry()
        with pytest.raises(TypeError):
            registry.register_detector("bad", "not_a_detector")

    def test_registry_repr(self, default_registry):
        r = repr(default_registry)
        assert "ModelRegistry" in r
        assert "clahe" in r


# ── Pipeline Full Run Tests ──────────────────────────────────────────


class TestMRIInferencePipeline:
    """Tests for the end-to-end inference pipeline."""

    def test_full_pipeline_2d(self, pipeline, sample_2d_image):
        """Full pipeline should run on a 2D image without errors."""
        result = pipeline.run(sample_2d_image)

        assert isinstance(result, InferenceOutput)
        assert result.success is True
        assert result.input_shape == (64, 64)
        assert result.total_duration_ms > 0
        assert result.pipeline_id is not None
        assert result.is_baseline is True
        assert len(result.summary) > 0

    def test_full_pipeline_3d(self, pipeline, sample_3d_volume):
        """Full pipeline should run on a 3D volume without errors."""
        result = pipeline.run(sample_3d_volume)

        assert result.success is True
        assert result.input_shape == (32, 32, 8)
        assert len(result.stage_results) >= 2  # preprocessing + enhancement/detection

    def test_pipeline_stages_order(self, pipeline, sample_2d_image):
        """Pipeline should execute stages in correct order."""
        result = pipeline.run(sample_2d_image)

        stages = [sr.stage for sr in result.stage_results]
        assert PipelineStage.PREPROCESSING in stages

        # With defaults, enhancement and detection should be present
        assert PipelineStage.ENHANCEMENT in stages
        assert PipelineStage.DETECTION in stages

    def test_pipeline_preprocessing_only(self, pipeline, sample_2d_image):
        """Pipeline with only preprocessing should work."""
        config = InferenceInput(
            enable_enhancement=False,
            enable_detection=False,
        )
        result = pipeline.run(sample_2d_image, config=config)

        assert result.success
        assert len(result.enhancement_results) == 0
        assert len(result.detection_results) == 0

    def test_pipeline_enhancement_only(self, pipeline, sample_2d_image):
        """Pipeline with preprocessing + enhancement only."""
        config = InferenceInput(
            enable_enhancement=True,
            enable_detection=False,
            enhancement_methods=["clahe"],
        )
        result = pipeline.run(sample_2d_image, config=config)

        assert result.success
        assert len(result.enhancement_results) == 1
        assert len(result.detection_results) == 0

    def test_pipeline_detection_only(self, pipeline, sample_2d_image):
        """Pipeline with preprocessing + detection only."""
        config = InferenceInput(
            enable_enhancement=False,
            enable_detection=True,
            detection_methods=["intensity_anomaly"],
        )
        result = pipeline.run(sample_2d_image, config=config)

        assert result.success
        assert len(result.enhancement_results) == 0
        assert len(result.detection_results) == 1

    def test_pipeline_multiple_enhancers(self, pipeline, sample_2d_image):
        """Pipeline should chain multiple enhancers in sequence."""
        config = InferenceInput(
            enable_enhancement=True,
            enable_detection=False,
            enhancement_methods=["gaussian_denoise", "clahe"],
        )
        result = pipeline.run(sample_2d_image, config=config)

        assert result.success
        assert len(result.enhancement_results) == 2

    def test_pipeline_multiple_detectors(self, pipeline, sample_2d_image):
        """Pipeline should run multiple detectors."""
        config = InferenceInput(
            enable_enhancement=False,
            enable_detection=True,
            detection_methods=["intensity_anomaly", "texture_anomaly"],
        )
        result = pipeline.run(sample_2d_image, config=config)

        assert result.success
        assert len(result.detection_results) == 2

    def test_pipeline_zscore_normalization(self, pipeline, sample_2d_image):
        """Pipeline should support z-score normalization."""
        config = InferenceInput(
            normalization_method="zscore",
            enable_enhancement=False,
            enable_detection=False,
        )
        result = pipeline.run(sample_2d_image, config=config)
        assert result.success

    def test_pipeline_no_normalization(self, pipeline, normalized_2d):
        """Pipeline should work without normalization on pre-normalized data."""
        config = InferenceInput(
            normalize=False,
            enable_enhancement=True,
            enable_detection=True,
            enhancement_methods=["clahe"],
            detection_methods=["intensity_anomaly"],
        )
        result = pipeline.run(normalized_2d, config=config)
        assert result.success

    def test_pipeline_custom_enhancement_params(self, pipeline, sample_2d_image):
        """Pipeline should pass custom params to enhancers."""
        config = InferenceInput(
            enable_enhancement=True,
            enable_detection=False,
            enhancement_methods=["clahe"],
            enhancement_params={"clahe": {"clip_limit": 4.0, "tile_grid_size": 4}},
        )
        result = pipeline.run(sample_2d_image, config=config)
        assert result.success

    def test_pipeline_custom_detection_params(self, pipeline, sample_2d_image):
        """Pipeline should pass custom params to detectors."""
        config = InferenceInput(
            enable_enhancement=False,
            enable_detection=True,
            detection_methods=["intensity_anomaly"],
            detection_confidence_threshold=0.1,
            detection_params={
                "intensity_anomaly": {"z_threshold": 2.0, "min_region_area": 5}
            },
        )
        result = pipeline.run(sample_2d_image, config=config)
        assert result.success

    def test_pipeline_unknown_enhancer_skipped(self, pipeline, sample_2d_image):
        """Unknown enhancer names should be skipped, not crash."""
        config = InferenceInput(
            enable_enhancement=True,
            enable_detection=False,
            enhancement_methods=["nonexistent_method", "clahe"],
        )
        result = pipeline.run(sample_2d_image, config=config)
        assert not result.success
        # Only CLAHE should have run
        assert len(result.enhancement_results) == 1

    def test_pipeline_unknown_detector_skipped(self, pipeline, sample_2d_image):
        """Unknown detector names should be skipped, not crash."""
        config = InferenceInput(
            enable_enhancement=False,
            enable_detection=True,
            detection_methods=["nonexistent_detector"],
        )
        result = pipeline.run(sample_2d_image, config=config)
        assert not result.success
        assert len(result.detection_results) == 0

    def test_pipeline_default_config(self, pipeline, sample_2d_image):
        """Pipeline should work with no explicit config (use defaults)."""
        result = pipeline.run(sample_2d_image)
        assert result.success

    def test_pipeline_creates_default_registry(self, sample_2d_image):
        """Pipeline created without registry should auto-create defaults."""
        pipeline = MRIInferencePipeline()
        result = pipeline.run(sample_2d_image)
        assert result.success


# ── Pipeline Error Handling Tests ────────────────────────────────────


class TestPipelineEdgeCases:
    """Edge cases and error handling for the inference pipeline."""

    def test_invalid_input_type(self, pipeline):
        """Non-ndarray input should produce failed output."""
        result = pipeline.run("not_an_array")
        assert not result.success
        assert result.error_message is not None

    def test_empty_array(self, pipeline):
        """Empty array should produce failed output."""
        result = pipeline.run(np.array([], dtype=np.float32))
        assert not result.success

    def test_1d_array(self, pipeline):
        """1D array should produce failed output."""
        result = pipeline.run(np.array([1.0, 2.0, 3.0], dtype=np.float32))
        assert not result.success

    def test_4d_array(self, pipeline):
        """4D array should produce failed output."""
        result = pipeline.run(np.random.rand(8, 8, 8, 3).astype(np.float32))
        assert not result.success

    def test_output_serializable(self, pipeline, sample_2d_image):
        """InferenceOutput should be JSON-serializable."""
        result = pipeline.run(sample_2d_image)
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert "pipeline_id" in json_str
        assert "stage_results" in json_str

    def test_uniform_image(self, pipeline):
        """Uniform image should not crash the pipeline."""
        img = np.full((32, 32), 500.0, dtype=np.float32)
        result = pipeline.run(img)
        assert result.success


# ── Schema Tests ─────────────────────────────────────────────────────


class TestSchemas:
    """Tests for inference schema validation."""

    def test_inference_input_defaults(self):
        config = InferenceInput()
        assert config.normalize is True
        assert config.normalization_method == "minmax"
        assert config.enable_enhancement is True
        assert config.enable_detection is True

    def test_inference_input_custom(self):
        config = InferenceInput(
            image_id="test-123",
            modality="CT",
            normalize=False,
            enable_enhancement=False,
            enable_detection=True,
            detection_methods=["texture_anomaly"],
            detection_confidence_threshold=0.7,
        )
        assert config.image_id == "test-123"
        assert config.modality == "CT"
        assert config.enable_enhancement is False
        assert config.detection_methods == ["texture_anomaly"]

    def test_pipeline_stage_result_schema(self):
        result = PipelineStageResult(
            stage=PipelineStage.PREPROCESSING,
            success=True,
            duration_ms=15.5,
            details={"normalization": "minmax"},
        )
        assert result.stage == PipelineStage.PREPROCESSING
        assert result.duration_ms == 15.5

    def test_pipeline_stage_enum_values(self):
        assert PipelineStage.PREPROCESSING == "preprocessing"
        assert PipelineStage.ENHANCEMENT == "enhancement"
        assert PipelineStage.DETECTION == "detection"
