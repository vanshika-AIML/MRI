"""Base classes and schemas for MRI abnormality detection.

Defines the abstract detector interface, detection configuration, region
descriptors, and structured detection results. All detectors produce
model-agnostic output suitable for API consumption or report generation.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class SeverityLevel(str, Enum):
    """Severity classification for detected abnormalities.

    NOTE: These are heuristic-derived labels from baseline detectors.
    They do NOT correspond to clinical grading systems.
    """

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AbnormalityRegion(BaseModel):
    """Describes a single detected abnormality region in a model-agnostic format.

    Coordinates use array indexing (row, col) relative to the input image.
    """

    region_id: str = Field(..., description="Unique identifier for this region")
    label: str = Field(
        ...,
        description="Abnormality type label (e.g., 'intensity_anomaly', 'texture_anomaly')",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection confidence score [0.0, 1.0]",
    )
    severity: SeverityLevel = Field(
        SeverityLevel.NONE,
        description="Heuristic severity classification",
    )
    bounding_box: Optional[Tuple[int, int, int, int]] = Field(
        None,
        description="Bounding box as (row_min, col_min, row_max, col_max)",
    )
    centroid: Optional[Tuple[float, float]] = Field(
        None,
        description="Center of the region (row, col) in pixel coordinates",
    )
    area_pixels: Optional[int] = Field(
        None,
        description="Number of pixels in the region",
    )
    mean_intensity: Optional[float] = Field(
        None,
        description="Mean intensity value within the region",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional detector-specific metadata",
    )


class DetectionConfig(BaseModel):
    """Configuration for an abnormality detection run."""

    detector_name: str = Field(..., description="Name/identifier of the detector")
    confidence_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to include a region in results",
    )
    max_regions: int = Field(
        50,
        ge=1,
        description="Maximum number of regions to return",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detector-specific parameters",
    )


class DetectionResult(BaseModel):
    """Structured result from an abnormality detection operation.

    DISCLAIMER: Results from baseline detectors are heuristic-based and are
    NOT suitable for clinical diagnosis. They serve as development placeholders
    until trained models are integrated.
    """

    detector_name: str = Field(..., description="Name of the detector that produced this result")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of detection",
    )
    input_shape: tuple = Field(..., description="Shape of the input array")
    regions: List[AbnormalityRegion] = Field(
        default_factory=list,
        description="Detected abnormality regions",
    )
    overall_abnormality_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Aggregated abnormality score for the entire image/volume [0, 1]",
    )
    overall_severity: SeverityLevel = Field(
        SeverityLevel.NONE,
        description="Overall severity level derived from detected regions",
    )
    summary: str = Field(
        "",
        description="Human-readable summary of detection findings",
    )
    is_baseline: bool = Field(
        True,
        description="True if result is from a baseline/heuristic detector (not a trained model)",
    )
    success: bool = Field(True, description="Whether detection completed without error")
    error_message: Optional[str] = Field(
        None, description="Error details if success is False"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional detection metadata",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseDetector(ABC):
    """Abstract base class for MRI abnormality detectors.

    Subclasses must implement `detect_2d` for single-slice detection.
    The `detect` method handles both 2D and 3D inputs.

    IMPORTANT: Baseline detectors use image-processing heuristics and provide
    development-grade results only. They do NOT claim clinical diagnostic accuracy.
    """

    detector_name: str = "base_detector"

    @abstractmethod
    def detect_2d(
        self,
        image: np.ndarray,
        config: DetectionConfig,
    ) -> List[AbnormalityRegion]:
        """Detect abnormalities in a single 2D MRI slice.

        Args:
            image: 2D float32 numpy array (H, W), expected in [0, 1] range.
            config: Detection configuration with thresholds and parameters.

        Returns:
            List of detected AbnormalityRegion objects.
        """
        ...

    def detect(
        self,
        image: np.ndarray,
        config: Optional[DetectionConfig] = None,
    ) -> DetectionResult:
        """Detect abnormalities in a 2D slice or 3D volume.

        For 3D volumes, detection is performed slice-by-slice along the last
        axis and regions are merged into a single result.

        Args:
            image: 2D (H, W) or 3D (H, W, D) float32 numpy array.
            config: Detection configuration. Uses defaults if None.

        Returns:
            DetectionResult with all detected regions and summary.
        """
        if config is None:
            config = DetectionConfig(detector_name=self.detector_name)

        try:
            self._validate_input(image)

            if image.ndim == 2:
                regions = self.detect_2d(image, config)
            elif image.ndim == 3:
                regions = self._detect_3d(image, config)
            else:
                raise ValueError(
                    f"Expected 2D or 3D array, got {image.ndim}D with shape {image.shape}"
                )

            # Apply confidence threshold and limit
            regions = [r for r in regions if r.confidence >= config.confidence_threshold]
            regions = sorted(regions, key=lambda r: r.confidence, reverse=True)
            regions = regions[: config.max_regions]

            # Compute overall score and severity
            overall_score = self._compute_overall_score(regions)
            overall_severity = self._score_to_severity(overall_score)
            summary = self._generate_summary(regions, overall_score, overall_severity)

            return DetectionResult(
                detector_name=self.detector_name,
                input_shape=image.shape,
                regions=regions,
                overall_abnormality_score=overall_score,
                overall_severity=overall_severity,
                summary=summary,
                is_baseline=True,
                success=True,
            )

        except Exception as e:
            logger.error(f"Detection failed ({self.detector_name}): {e}")
            return DetectionResult(
                detector_name=self.detector_name,
                input_shape=image.shape if isinstance(image, np.ndarray) else (0,),
                regions=[],
                overall_abnormality_score=0.0,
                overall_severity=SeverityLevel.NONE,
                summary=f"Detection failed: {e}",
                is_baseline=True,
                success=False,
                error_message=str(e),
            )

    def _detect_3d(
        self,
        volume: np.ndarray,
        config: DetectionConfig,
    ) -> List[AbnormalityRegion]:
        """Apply 2D detection slice-by-slice on a 3D volume."""
        all_regions: List[AbnormalityRegion] = []
        for z in range(volume.shape[2]):
            slice_2d = volume[:, :, z]
            regions = self.detect_2d(slice_2d, config)
            # Tag each region with the slice index
            for region in regions:
                region.metadata["slice_index"] = z
            all_regions.extend(regions)
        return all_regions

    @staticmethod
    def _compute_overall_score(regions: List[AbnormalityRegion]) -> float:
        """Compute an aggregated abnormality score from detected regions."""
        if not regions:
            return 0.0
        # Use max confidence as overall score (conservative estimate)
        max_conf = max(r.confidence for r in regions)
        # Modulate slightly by number of regions (more regions = slightly higher score)
        region_factor = min(1.0, 0.7 + 0.3 * min(len(regions) / 10.0, 1.0))
        return round(min(1.0, max_conf * region_factor), 4)

    @staticmethod
    def _score_to_severity(score: float) -> SeverityLevel:
        """Map an abnormality score to a severity level."""
        if score < 0.25:
            return SeverityLevel.NONE
        elif score < 0.5:
            return SeverityLevel.LOW
        elif score < 0.75:
            return SeverityLevel.MODERATE
        else:
            return SeverityLevel.HIGH

    @staticmethod
    def _generate_summary(
        regions: List[AbnormalityRegion],
        overall_score: float,
        overall_severity: SeverityLevel,
    ) -> str:
        """Generate a human-readable summary of detection findings."""
        if not regions:
            return (
                "No candidate regions were returned by the baseline heuristic detector. "
                "Unable to assess this scan reliably; this is not evidence that the scan is normal."
            )

        region_labels = [r.label for r in regions]
        unique_labels = sorted(set(region_labels))
        label_summary = ", ".join(
            f"{label} ({region_labels.count(label)})" for label in unique_labels
        )

        return (
            f"Baseline detector identified {len(regions)} potential region(s): "
            f"{label_summary}. Overall score: {overall_score:.2f} "
            f"({overall_severity.value}). "
            f"WARNING: These are heuristic-based findings and NOT clinical diagnoses."
        )

    @staticmethod
    def _validate_input(image: np.ndarray) -> None:
        """Validate input array type and dimensionality."""
        if not isinstance(image, np.ndarray):
            raise TypeError(f"Expected numpy ndarray, got {type(image).__name__}")
        if image.ndim not in (2, 3):
            raise ValueError(
                f"Expected 2D or 3D array, got {image.ndim}D with shape {image.shape}"
            )
        if image.size == 0:
            raise ValueError("Input array is empty")
