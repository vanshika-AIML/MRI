"""Contrast enhancement methods for MRI slices.

Implements CLAHE (Contrast Limited Adaptive Histogram Equalization) and
standard histogram equalization using OpenCV. Both methods operate on
normalized [0, 1] float32 images.
"""

import logging
from typing import Any

import cv2
import numpy as np

from ml.enhancement.base import BaseEnhancer, EnhancementMethod

logger = logging.getLogger(__name__)


class CLAHEEnhancer(BaseEnhancer):
    """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).

    CLAHE enhances local contrast while preventing noise amplification through
    a contrast-limiting clip parameter. Effective for improving visibility of
    soft-tissue boundaries in MRI.

    Default parameters are tuned for general MRI development/testing and are
    NOT validated for any clinical application.
    """

    method = EnhancementMethod.CLAHE

    def enhance_2d(
        self,
        image: np.ndarray,
        clip_limit: float = 2.0,
        tile_grid_size: int = 8,
        **kwargs: Any,
    ) -> np.ndarray:
        """Apply CLAHE to a single 2D slice.

        Args:
            image: 2D float32 array in [0, 1] range.
            clip_limit: CLAHE contrast clip limit (higher = more contrast).
            tile_grid_size: Size of the contextual regions for histogram equalization.

        Returns:
            Enhanced 2D float32 array in [0, 1] range.
        """
        # Convert to 8-bit for OpenCV CLAHE
        img_uint8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)

        clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=(tile_grid_size, tile_grid_size),
        )
        enhanced_uint8 = clahe.apply(img_uint8)

        # Convert back to float32 [0, 1]
        return enhanced_uint8.astype(np.float32) / 255.0


class HistogramEqualizationEnhancer(BaseEnhancer):
    """Apply standard global histogram equalization.

    Spreads pixel intensities across the full dynamic range. Useful as a
    simple baseline enhancement but may amplify noise in low-signal regions.
    """

    method = EnhancementMethod.HISTOGRAM_EQUALIZATION

    def enhance_2d(self, image: np.ndarray, **kwargs: Any) -> np.ndarray:
        """Apply global histogram equalization to a single 2D slice.

        Args:
            image: 2D float32 array in [0, 1] range.

        Returns:
            Enhanced 2D float32 array in [0, 1] range.
        """
        img_uint8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        enhanced_uint8 = cv2.equalizeHist(img_uint8)
        return enhanced_uint8.astype(np.float32) / 255.0
