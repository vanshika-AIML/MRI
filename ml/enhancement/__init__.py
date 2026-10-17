"""MRI Image Enhancement Package.

Provides contrast enhancement, denoising, and sharpening operations
for 2D MRI slices and 3D volumes. Enhancement methods are modular and
can be used standalone or as part of the inference pipeline.

NOTE: These are computational image-processing techniques for development
and research purposes. They are NOT validated for clinical diagnostic use.
"""

from ml.enhancement.base import BaseEnhancer, EnhancementConfig, EnhancementResult
from ml.enhancement.contrast import CLAHEEnhancer, HistogramEqualizationEnhancer
from ml.enhancement.denoise import GaussianDenoiser, NonLocalMeansDenoiser
from ml.enhancement.sharpening import UnsharpMaskEnhancer

__all__ = [
    "BaseEnhancer",
    "EnhancementConfig",
    "EnhancementResult",
    "CLAHEEnhancer",
    "HistogramEqualizationEnhancer",
    "GaussianDenoiser",
    "NonLocalMeansDenoiser",
    "UnsharpMaskEnhancer",
]
