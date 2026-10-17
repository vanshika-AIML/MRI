"""MRI Inference Pipeline.

Orchestrates the end-to-end flow: preprocessing → enhancement → detection → result.
Model loading and configuration are handled by the model registry (ml.models.registry),
keeping inference logic decoupled from model management.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

from ml.detection.base import BaseDetector, DetectionConfig, DetectionResult
from ml.enhancement.base import BaseEnhancer, EnhancementResult
from ml.inference.schemas import (
    InferenceInput,
    InferenceOutput,
    PipelineStage,
    PipelineStageResult,
)
from ml.models.registry import ModelRegistry
from ml.preprocessing.transforms import (
    normalize_intensity_minmax,
    normalize_intensity_zscore,
    percentile_clipping,
)

logger = logging.getLogger(__name__)


class MRIInferencePipeline:
    """End-to-end MRI analysis pipeline.

    Chains preprocessing, enhancement, and detection stages using modular,
    pluggable components from the model registry. Each stage is optional
    and can be configured through InferenceInput.

    Usage:
        registry = ModelRegistry()
        # Register enhancers and detectors (or use defaults)
        registry.register_enhancer("clahe", CLAHEEnhancer())
        registry.register_detector("intensity_anomaly", IntensityAnomalyDetector())

        pipeline = MRIInferencePipeline(registry=registry)
        result = pipeline.run(image_array, config=InferenceInput())
    """

    def __init__(self, registry: Optional[ModelRegistry] = None):
        """Initialize the inference pipeline.

        Args:
            registry: ModelRegistry providing enhancers and detectors.
                     If None, a default registry with baseline models is created.
        """
        if registry is None:
            registry = ModelRegistry.create_default()
        self.registry = registry

    def run(
        self,
        image: np.ndarray,
        config: Optional[InferenceInput] = None,
    ) -> InferenceOutput:
        """Execute the full inference pipeline.

        Args:
            image: 2D (H, W) or 3D (H, W, D) numpy array of MRI data.
            config: Pipeline configuration. Uses defaults if None.

        Returns:
            InferenceOutput with results from all stages.
        """
        pipeline_start = time.perf_counter()
        pipeline_id = uuid.uuid4().hex[:12]

        if config is None:
            config = InferenceInput()

        stage_results: List[PipelineStageResult] = []
        enhancement_results: List[EnhancementResult] = []
        detection_results: List[DetectionResult] = []

        try:
            self._validate_input(image)
            input_shape = image.shape
            current_image = image.astype(np.float32)

            # Stage 1: Preprocessing
            preprocess_result, current_image = self._run_preprocessing(
                current_image, config
            )
            stage_results.append(preprocess_result)

            # Stage 2: Enhancement
            if config.enable_enhancement:
                enhance_result, current_image, enh_details = self._run_enhancement(
                    current_image, config
                )
                stage_results.append(enhance_result)
                enhancement_results.extend(enh_details)

            # Stage 3: Detection
            if config.enable_detection:
                detect_result, det_details = self._run_detection(
                    current_image, config
                )
                stage_results.append(detect_result)
                detection_results.extend(det_details)

            total_ms = (time.perf_counter() - pipeline_start) * 1000.0
            summary = self._build_summary(
                enhancement_results, detection_results, total_ms
            )

            output = InferenceOutput(
                pipeline_id=pipeline_id,
                input_config=config,
                input_shape=input_shape,
                stage_results=stage_results,
                enhancement_results=enhancement_results,
                detection_results=detection_results,
                total_duration_ms=round(total_ms, 2),
                success=all(stage.success for stage in stage_results),
                error_message=None if all(stage.success for stage in stage_results) else "One or more requested pipeline stages failed.",
                is_baseline=True,
                summary=summary if all(stage.success for stage in stage_results) else "Pipeline incomplete: one or more requested stages failed. Review stage results.",
            )
            # Attach processed image for downstream use (not serialized)
            output._processed_image = current_image
            return output

        except Exception as e:
            total_ms = (time.perf_counter() - pipeline_start) * 1000.0
            logger.error(f"Pipeline failed: {e}")
            return InferenceOutput(
                pipeline_id=pipeline_id,
                input_config=config,
                input_shape=image.shape if isinstance(image, np.ndarray) else (0,),
                stage_results=stage_results,
                enhancement_results=enhancement_results,
                detection_results=detection_results,
                total_duration_ms=round(total_ms, 2),
                success=False,
                error_message=str(e),
                is_baseline=True,
                summary=f"Pipeline failed: {e}",
            )

    def _run_preprocessing(
        self,
        image: np.ndarray,
        config: InferenceInput,
    ) -> tuple:
        """Run the preprocessing stage."""
        start = time.perf_counter()
        details: Dict[str, Any] = {}

        try:
            processed = image.copy()

            if config.normalize:
                method = config.normalization_method.lower()

                if method == "minmax":
                    processed = normalize_intensity_minmax(
                        processed,
                        min_val=0.0,
                        max_val=1.0,
                        clip_percentiles=config.clip_percentiles,
                    )
                    details["normalization"] = "minmax"

                elif method == "zscore":
                    processed = normalize_intensity_zscore(processed)
                    details["normalization"] = "zscore"

                else:
                    # Default to minmax
                    processed = normalize_intensity_minmax(
                        processed, min_val=0.0, max_val=1.0
                    )
                    details["normalization"] = f"minmax (fallback from '{method}')"

                details["output_range"] = (
                    float(np.min(processed)),
                    float(np.max(processed)),
                )

            duration_ms = (time.perf_counter() - start) * 1000.0

            result = PipelineStageResult(
                stage=PipelineStage.PREPROCESSING,
                success=True,
                duration_ms=round(duration_ms, 2),
                details=details,
            )
            return result, processed

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            result = PipelineStageResult(
                stage=PipelineStage.PREPROCESSING,
                success=False,
                duration_ms=round(duration_ms, 2),
                details=details,
                error_message=str(e),
            )
            return result, image

    def _run_enhancement(
        self,
        image: np.ndarray,
        config: InferenceInput,
    ) -> tuple:
        """Run the enhancement stage with one or more enhancers."""
        start = time.perf_counter()
        details: Dict[str, Any] = {}
        enh_results: List[EnhancementResult] = []

        try:
            current_image = image.copy()

            for method_name in config.enhancement_methods:
                enhancer = self.registry.get_enhancer(method_name)
                if enhancer is None:
                    logger.warning(f"Enhancer '{method_name}' not found in registry, skipping")
                    details[method_name] = "unknown method"
                    continue

                # Get method-specific params
                params = config.enhancement_params.get(method_name, {})

                enh_result = enhancer.enhance(current_image, **params)
                enh_results.append(enh_result)

                if enh_result.success:
                    current_image = enh_result._enhanced_array
                    details[method_name] = "applied"
                else:
                    details[method_name] = f"failed: {enh_result.error_message}"

            duration_ms = (time.perf_counter() - start) * 1000.0

            stage_result = PipelineStageResult(
                stage=PipelineStage.ENHANCEMENT,
                success=all(r.success for r in enh_results) and len(enh_results) == len(config.enhancement_methods),
                duration_ms=round(duration_ms, 2),
                details=details,
            )
            return stage_result, current_image, enh_results

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            stage_result = PipelineStageResult(
                stage=PipelineStage.ENHANCEMENT,
                success=False,
                duration_ms=round(duration_ms, 2),
                details=details,
                error_message=str(e),
            )
            return stage_result, image, enh_results

    def _run_detection(
        self,
        image: np.ndarray,
        config: InferenceInput,
    ) -> tuple:
        """Run the detection stage with one or more detectors."""
        start = time.perf_counter()
        details: Dict[str, Any] = {}
        det_results: List[DetectionResult] = []

        try:
            for method_name in config.detection_methods:
                detector = self.registry.get_detector(method_name)
                if detector is None:
                    logger.warning(f"Detector '{method_name}' not found in registry, skipping")
                    details[method_name] = "unknown method"
                    continue

                det_config = DetectionConfig(
                    detector_name=method_name,
                    confidence_threshold=config.detection_confidence_threshold,
                    params=config.detection_params.get(method_name, {}),
                )

                det_result = detector.detect(image, config=det_config)
                det_results.append(det_result)

                details[method_name] = {
                    "regions_found": len(det_result.regions),
                    "overall_score": det_result.overall_abnormality_score,
                    "success": det_result.success,
                }

            duration_ms = (time.perf_counter() - start) * 1000.0

            stage_result = PipelineStageResult(
                stage=PipelineStage.DETECTION,
                success=all(r.success for r in det_results) and len(det_results) == len(config.detection_methods),
                duration_ms=round(duration_ms, 2),
                details=details,
            )
            return stage_result, det_results

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            stage_result = PipelineStageResult(
                stage=PipelineStage.DETECTION,
                success=False,
                duration_ms=round(duration_ms, 2),
                details=details,
                error_message=str(e),
            )
            return stage_result, det_results

    @staticmethod
    def _validate_input(image: np.ndarray) -> None:
        """Validate pipeline input."""
        if not isinstance(image, np.ndarray):
            raise TypeError(f"Expected numpy ndarray, got {type(image).__name__}")
        if image.ndim not in (2, 3):
            raise ValueError(
                f"Expected 2D or 3D array, got {image.ndim}D with shape {image.shape}"
            )
        if not np.issubdtype(image.dtype, np.number) or not np.isfinite(image).all():
            raise ValueError("Input must contain finite numeric values")
        if image.size == 0:
            raise ValueError("Input array is empty")

    @staticmethod
    def _build_summary(
        enhancement_results: List[EnhancementResult],
        detection_results: List[DetectionResult],
        total_ms: float,
    ) -> str:
        """Build a human-readable summary of the full pipeline run."""
        parts = [f"Pipeline completed in {total_ms:.0f}ms."]

        if enhancement_results:
            methods = [r.method.value for r in enhancement_results if r.success]
            if methods:
                parts.append(f"Enhancement: {', '.join(methods)} applied.")

        if detection_results:
            total_regions = sum(len(r.regions) for r in detection_results)
            if total_regions > 0:
                parts.append(
                    f"Detection: {total_regions} potential region(s) identified."
                )
            else:
                parts.append(
                    "Detection: no candidate regions returned; unable to assess this scan reliably."
                )

        parts.append(
            "NOTE: Baseline heuristic results only — not for clinical use."
        )

        return " ".join(parts)
