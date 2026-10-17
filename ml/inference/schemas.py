"""Typed input/output schemas for the MRI inference pipeline.

Defines structured Pydantic models for pipeline input configuration,
per-stage results, and the complete inference output. These schemas
are designed to be serializable for API consumption and report generation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ml.detection.base import DetectionResult
from ml.enhancement.base import EnhancementResult


class PipelineStage(str, Enum):
    """Identifiers for each stage of the inference pipeline."""

    PREPROCESSING = "preprocessing"
    ENHANCEMENT = "enhancement"
    DETECTION = "detection"


class PipelineStageResult(BaseModel):
    """Result from a single pipeline stage."""

    stage: PipelineStage = Field(..., description="Pipeline stage identifier")
    success: bool = Field(True, description="Whether the stage completed successfully")
    duration_ms: float = Field(0.0, description="Execution time in milliseconds")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Stage-specific details"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if stage failed"
    )


class InferenceInput(BaseModel):
    """Configuration and metadata for a pipeline inference run.

    The actual image/volume data is passed separately as a numpy array.
    This schema captures configuration parameters and metadata.
    """

    image_id: Optional[str] = Field(None, description="Identifier for the input image/volume")
    source_format: Optional[str] = Field(
        None, description="Source format (e.g., 'dicom', 'nifti', 'numpy')"
    )
    modality: str = Field("MR", description="Imaging modality (MR, CT, etc.)")

    # Preprocessing options
    normalize: bool = Field(True, description="Apply intensity normalization")
    normalization_method: str = Field(
        "minmax",
        description="Normalization method: 'minmax', 'zscore', or 'windowing'",
    )
    clip_percentiles: Optional[Tuple[float, float]] = Field(
        (1.0, 99.0), description="Percentile clipping bounds for normalization"
    )

    # Enhancement options
    enable_enhancement: bool = Field(True, description="Enable image enhancement stage")
    enhancement_methods: List[str] = Field(
        default_factory=lambda: ["clahe"],
        description="Enhancement methods to apply (in order)",
    )
    enhancement_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for enhancement methods",
    )

    # Detection options
    enable_detection: bool = Field(True, description="Enable abnormality detection stage")
    detection_methods: List[str] = Field(
        default_factory=lambda: ["intensity_anomaly"],
        description="Detection methods to apply",
    )
    detection_confidence_threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for detection results",
    )
    detection_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for detection methods",
    )


class InferenceOutput(BaseModel):
    """Complete output from the MRI inference pipeline.

    Aggregates results from all pipeline stages into a single structured
    document suitable for API responses and report generation.

    DISCLAIMER: Results from baseline detectors are heuristic-based and
    NOT suitable for clinical diagnosis.
    """

    pipeline_id: str = Field(..., description="Unique pipeline run identifier")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of pipeline execution",
    )
    input_config: InferenceInput = Field(
        ..., description="Input configuration used for this run"
    )
    input_shape: tuple = Field(..., description="Shape of the input array")

    # Stage results
    stage_results: List[PipelineStageResult] = Field(
        default_factory=list,
        description="Results from each pipeline stage in execution order",
    )

    # Enhancement summary
    enhancement_results: List[EnhancementResult] = Field(
        default_factory=list,
        description="Detailed results from enhancement stage(s)",
    )

    # Detection summary
    detection_results: List[DetectionResult] = Field(
        default_factory=list,
        description="Detailed results from detection method(s)",
    )

    # Pipeline-level summary
    total_duration_ms: float = Field(0.0, description="Total pipeline execution time in ms")
    success: bool = Field(True, description="Whether the entire pipeline succeeded")
    error_message: Optional[str] = Field(
        None, description="Error details if pipeline failed"
    )
    is_baseline: bool = Field(
        True,
        description="True if only baseline/heuristic methods were used (no trained models)",
    )
    summary: str = Field(
        "",
        description="Human-readable summary of all pipeline findings",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
