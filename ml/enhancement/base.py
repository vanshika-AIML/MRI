"""Base classes and schemas for MRI image enhancement.

All enhancers inherit from BaseEnhancer, which defines a common interface
for configuration, execution, and result reporting.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class EnhancementMethod(str, Enum):
    """Supported enhancement method identifiers."""

    CLAHE = "clahe"
    HISTOGRAM_EQUALIZATION = "histogram_equalization"
    GAUSSIAN_DENOISE = "gaussian_denoise"
    NON_LOCAL_MEANS_DENOISE = "non_local_means_denoise"
    UNSHARP_MASK = "unsharp_mask"


class EnhancementConfig(BaseModel):
    """Configuration parameters for an enhancement operation."""

    method: EnhancementMethod = Field(..., description="Enhancement method to apply")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method-specific parameters")
    apply_to_3d: bool = Field(
        False,
        description="If True, apply enhancement slice-by-slice to a 3D volume",
    )


class EnhancementResult(BaseModel):
    """Structured result from an enhancement operation."""

    method: EnhancementMethod = Field(..., description="Method that was applied")
    input_shape: tuple = Field(..., description="Shape of the input array")
    output_shape: tuple = Field(..., description="Shape of the output array")
    input_intensity_range: tuple = Field(
        ..., description="(min, max) intensity of input"
    )
    output_intensity_range: tuple = Field(
        ..., description="(min, max) intensity of output"
    )
    parameters_used: Dict[str, Any] = Field(
        default_factory=dict, description="Actual parameters applied"
    )
    success: bool = Field(True, description="Whether enhancement completed without error")
    error_message: Optional[str] = Field(None, description="Error details if success is False")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseEnhancer(ABC):
    """Abstract base class for all MRI image enhancers.

    Subclasses must implement `enhance_2d` for single-slice enhancement.
    The `enhance` method handles both 2D and 3D arrays, applying slice-by-slice
    processing for volumes.
    """

    method: EnhancementMethod

    @abstractmethod
    def enhance_2d(self, image: np.ndarray, **kwargs: Any) -> np.ndarray:
        """Enhance a single 2D MRI slice.

        Args:
            image: 2D float32 numpy array (H, W), expected in [0, 1] range.
            **kwargs: Method-specific parameters.

        Returns:
            Enhanced 2D float32 numpy array.
        """
        ...

    def enhance(self, image: np.ndarray, **kwargs: Any) -> EnhancementResult:
        """Enhance a 2D slice or 3D volume and return a structured result.

        For 3D volumes, enhancement is applied slice-by-slice along the last axis.

        Args:
            image: 2D (H, W) or 3D (H, W, D) float32 numpy array.
            **kwargs: Method-specific parameters passed to enhance_2d.

        Returns:
            EnhancementResult with metadata. The enhanced array is stored
            in the `_enhanced_array` attribute (not serialized in the schema).
        """
        try:
            self._validate_input(image)
            input_range = (float(np.min(image)), float(np.max(image)))

            if image.ndim == 2:
                enhanced = self.enhance_2d(image, **kwargs)
            elif image.ndim == 3:
                enhanced = self._enhance_3d(image, **kwargs)
            else:
                raise ValueError(
                    f"Expected 2D or 3D array, got {image.ndim}D with shape {image.shape}"
                )

            output_range = (float(np.min(enhanced)), float(np.max(enhanced)))

            result = EnhancementResult(
                method=self.method,
                input_shape=image.shape,
                output_shape=enhanced.shape,
                input_intensity_range=input_range,
                output_intensity_range=output_range,
                parameters_used=kwargs,
                success=True,
            )
            # Attach array as non-serialized attribute for pipeline consumption
            result._enhanced_array = enhanced
            return result

        except Exception as e:
            logger.error(f"Enhancement failed ({self.method.value}): {e}")
            result = EnhancementResult(
                method=self.method,
                input_shape=image.shape if isinstance(image, np.ndarray) else (0,),
                output_shape=(0,),
                input_intensity_range=(0.0, 0.0),
                output_intensity_range=(0.0, 0.0),
                parameters_used=kwargs,
                success=False,
                error_message=str(e),
            )
            result._enhanced_array = image  # Return original on failure
            return result

    def _enhance_3d(self, volume: np.ndarray, **kwargs: Any) -> np.ndarray:
        """Apply 2D enhancement slice-by-slice along the last axis of a 3D volume."""
        enhanced_slices = []
        for z in range(volume.shape[2]):
            slice_2d = volume[:, :, z]
            enhanced_slices.append(self.enhance_2d(slice_2d, **kwargs))
        return np.stack(enhanced_slices, axis=2)

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
