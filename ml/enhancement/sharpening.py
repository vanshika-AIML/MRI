"""Sharpening methods for MRI slices.

Implements unsharp masking to enhance edge and tissue boundary visibility.
"""

import logging
from typing import Any

import cv2
import numpy as np

from ml.enhancement.base import BaseEnhancer, EnhancementMethod

logger = logging.getLogger(__name__)


class UnsharpMaskEnhancer(BaseEnhancer):
    """Unsharp Mask sharpening.

    Enhances edges by subtracting a blurred version of the image and adding
    the high-frequency detail back with a controllable strength factor.
    Useful for improving tissue boundary visibility in MRI slices.
    """

    method = EnhancementMethod.UNSHARP_MASK

    def enhance_2d(
        self,
        image: np.ndarray,
        sigma: float = 1.0,
        strength: float = 1.5,
        **kwargs: Any,
    ) -> np.ndarray:
        """Apply unsharp mask sharpening to a single 2D slice.

        Args:
            image: 2D float32 array in [0, 1] range.
            sigma: Gaussian blur sigma for the low-pass component.
            strength: Multiplier for the high-pass (detail) component.

        Returns:
            Sharpened 2D float32 array clipped to [0, 1] range.
        """
        blurred = cv2.GaussianBlur(
            image.astype(np.float32),
            ksize=(0, 0),  # Auto-derive kernel size from sigma
            sigmaX=sigma,
            sigmaY=sigma,
        )

        # detail = image - blurred (high-pass)
        sharpened = image.astype(np.float32) + strength * (image.astype(np.float32) - blurred)
        return np.clip(sharpened, 0.0, 1.0)
