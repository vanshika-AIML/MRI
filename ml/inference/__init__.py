"""MRI Inference Pipeline Package.

Provides the end-to-end inference pipeline that chains preprocessing,
enhancement, and detection into a single composable workflow with
structured, typed input/output schemas.
"""

from ml.inference.schemas import (
    InferenceInput,
    InferenceOutput,
    PipelineStageResult,
    PipelineStage,
)
from ml.inference.pipeline import MRIInferencePipeline

__all__ = [
    "InferenceInput",
    "InferenceOutput",
    "PipelineStageResult",
    "PipelineStage",
    "MRIInferencePipeline",
]
