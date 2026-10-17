"""Pydantic schemas for MRI AI Inference API (Phase 6).

Defines typed request options, detected region descriptors, input metadata,
and structured API responses. Incorporates mandatory clinical disclaimers
and severity ratings.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

CLINICAL_DISCLAIMER: str = (
    "RESEARCH-ONLY DISCLAIMER: This system provides experimental image processing, "
    "heuristic indicators, or segmentation predictions for technical research only. "
    "It does NOT provide a clinical diagnosis, medical opinion, or confirmed lesion "
    "classification. Model masks and scores are not clinical probabilities and may "
    "be wrong. Outputs require independent review by a qualified medical professional "
    "and must not guide patient care."
)


class DetectedRegionSchema(BaseModel):
    """Schema for a single detected anatomical or intensity abnormality region."""

    region_id: str = Field(..., description="Unique region identifier within analysis")
    bbox: List[int] = Field(
        ...,
        description="Bounding box coordinates [y_min, x_min, y_max, x_max] or 3D bounding box",
    )
    centroid: List[float] = Field(..., description="Centroid coordinates of detected region")
    area_pixels: int = Field(..., description="Area or volume size of region in pixels/voxels")
    mean_intensity: float = Field(..., description="Mean signal intensity in region")
    max_intensity: float = Field(..., description="Maximum signal intensity in region")
    anomaly_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Mathematical anomaly score (0.0 to 1.0)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection confidence score (NOT clinical probability)",
    )
    severity: str = Field(
        "low",
        description="Heuristic severity level: 'low', 'medium', or 'high'",
    )
    slice_index: Optional[int] = Field(
        None,
        description="Z-slice index if detected in a 3D volume",
    )


class InputMetadataSchema(BaseModel):
    """Metadata regarding the processed MRI input file/volume."""

    filename: str = Field(..., description="Sanitized original filename")
    source_format: str = Field(..., description="File format (dicom, nifti, png, jpeg, npy)")
    dimensions: List[int] = Field(..., description="Array dimensions/shape [H, W] or [H, W, D]")
    ndim: int = Field(..., description="Number of array dimensions (2 or 3)")
    modality: str = Field("MR", description="Imaging modality (default: MR)")
    patient_id: Optional[str] = Field(None, description="Patient identifier if extracted")
    study_instance_uid: Optional[str] = Field(None, description="Study Instance UID if extracted")
    series_instance_uid: Optional[str] = Field(None, description="Series Instance UID if extracted")
    sequence_confirmed_by_user: Optional[bool] = Field(
        None,
        description="Whether the uploader declared the sequence; this is not independently verified",
    )


class StageResultSchema(BaseModel):
    """Summary result of a pipeline stage execution."""

    stage: str = Field(..., description="Stage name (preprocessing, enhancement, detection)")
    success: bool = Field(True, description="Whether stage executed without fatal error")
    duration_ms: float = Field(0.0, description="Stage processing duration in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Stage execution metrics")
    error_message: Optional[str] = Field(None, description="Error message if stage failed")


class AnalysisOptions(BaseModel):
    """Optional configuration parameters for inference run."""

    normalize: bool = Field(True, description="Apply intensity normalization")
    normalization_method: str = Field(
        "minmax", description="Normalization algorithm: 'minmax' or 'zscore'"
    )
    enable_enhancement: bool = Field(True, description="Enable image enhancement stage")
    enhancement_methods: List[str] = Field(
        default_factory=lambda: ["clahe"],
        description="Enhancement methods to apply ('clahe', 'histeq', 'gaussian', 'unsharp')",
    )
    enable_detection: bool = Field(True, description="Enable abnormality detection stage")
    detection_methods: List[str] = Field(
        default_factory=lambda: ["intensity_anomaly"],
        description="Detection algorithms to apply ('intensity_anomaly', 'texture_anomaly')",
    )
    confidence_threshold: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum confidence score threshold for detections"
    )
    study_id: Optional[str] = Field(None, description="Optional associated study ID UUID string")


class SegmentationPredictionSchema(BaseModel):
    """Research segmentation artifact and model provenance."""

    target: str
    modality: str
    mask_format: str
    mask_nifti_gz_base64: str
    overlay_format: str
    overlay_png_base64: str
    preview_slice_index: int
    mask_dimensions: List[int]
    affine: List[List[float]]
    voxel_spacing_mm: List[float]
    predicted_voxels: int
    threshold: float
    preprocessing_version: str
    checkpoint_sha256: str
    input_sha256: str
    mask_sha256: str


class AnalysisResponse(BaseModel):
    """Complete structured API response for Phase 6 MRI AI Inference."""

    analysis_id: str = Field(..., description="Unique analysis job identifier")
    status: str = Field("completed", description="Status ('completed' or 'failed')")
    success: bool = Field(True, description="Overall pipeline success indicator")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC execution timestamp",
    )
    input_metadata: InputMetadataSchema = Field(..., description="Metadata of processed MRI input")
    model_name: str = Field(
        "baseline_mri_pipeline", description="Name of inference pipeline or active model"
    )
    model_version: str = Field("1.0.0", description="Version of inference pipeline")
    is_baseline: bool = Field(
        True,
        description="True if heuristic/baseline detectors were used without trained networks",
    )
    total_duration_ms: float = Field(..., description="Total pipeline execution time in ms")
    severity: str = Field(
        "not_assessed",
        description="Nonclinical assessment status; an empty heuristic result is not a normal finding",
    )
    overall_confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Peak anomaly confidence score across detected regions",
    )
    detected_regions_count: int = Field(0, description="Total count of detected abnormal regions")
    detected_regions: List[DetectedRegionSchema] = Field(
        default_factory=list, description="List of detected anomaly regions"
    )
    prediction: Optional[SegmentationPredictionSchema] = Field(
        None, description="Research segmentation artifact; absent for heuristic analyses"
    )
    stage_results: List[StageResultSchema] = Field(
        default_factory=list, description="Per-stage pipeline execution metrics"
    )
    summary: str = Field("", description="Human-readable pipeline summary")
    warnings: List[str] = Field(default_factory=list, description="Warning messages if any")
    error_message: Optional[str] = Field(None, description="Error detail if pipeline failed")
    clinical_disclaimer: str = Field(
        CLINICAL_DISCLAIMER, description="Mandatory clinical disclaimer"
    )
