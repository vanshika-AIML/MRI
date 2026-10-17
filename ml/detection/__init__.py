"""MRI Abnormality Detection Package.

Provides interfaces and baseline implementations for detecting abnormalities
in MRI slices and volumes. Detection models produce structured, model-agnostic
results with confidence/probability scores and region information.

IMPORTANT DISCLAIMER:
    These are development/research baseline implementations. They use simple
    statistical and image-processing heuristics, NOT trained deep learning models.
    They do NOT provide clinical diagnostic accuracy and MUST NOT be used for
    medical decision-making. Real trained models can be plugged into the same
    interfaces when available.
"""

from ml.detection.base import (
    BaseDetector,
    DetectionConfig,
    DetectionResult,
    AbnormalityRegion,
    SeverityLevel,
)
from ml.detection.intensity_detector import IntensityAnomalyDetector
from ml.detection.texture_detector import TextureAnomalyDetector

__all__ = [
    "BaseDetector",
    "DetectionConfig",
    "DetectionResult",
    "AbnormalityRegion",
    "SeverityLevel",
    "IntensityAnomalyDetector",
    "TextureAnomalyDetector",
]
