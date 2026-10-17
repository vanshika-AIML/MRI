"""Denoising methods for MRI slices.

Implements Gaussian smoothing and Non-Local Means denoising. Both operate
on normalized [0, 1] float32 images and return the same range.
"""

import logging
from typing import Any

import cv2
import numpy as np

from ml.enhancement.base import BaseEnhancer, EnhancementMethod

logger = logging.getLogger(__name__)


class GaussianDenoiser(BaseEnhancer):
    """Gaussian blur-based denoiser.

    Applies isotropic Gaussian smoothing to reduce high-frequency noise.
    Simple but effective for Rician-like MRI noise when moderate sigma is used.
    """

    method = EnhancementMethod.GAUSSIAN_DENOISE

    def enhance_2d(
        self,
        image: np.ndarray,
        kernel_size: int = 5,
        sigma: float = 1.0,
        **kwargs: Any,
    ) -> np.ndarray:
        """Apply Gaussian denoising to a single 2D slice.

        Args:
            image: 2D float32 array in [0, 1] range.
            kernel_size: Size of the Gaussian kernel (must be odd).
            sigma: Standard deviation of the Gaussian kernel.

        Returns:
            Denoised 2D float32 array in [0, 1] range.
        """
        # Ensure kernel_size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        denoised = cv2.GaussianBlur(
            image.astype(np.float32),
            ksize=(kernel_size, kernel_size),
            sigmaX=sigma,
            sigmaY=sigma,
        )
        return np.clip(denoised, 0.0, 1.0)


class NonLocalMeansDenoiser(BaseEnhancer):
    """Non-Local Means denoising.

    Exploits self-similarity in image patches to denoise while preserving
    edges and fine structures better than simple Gaussian smoothing.
    Particularly well-suited for MRI where tissue boundaries carry diagnostic
    significance.
    """

    method = EnhancementMethod.NON_LOCAL_MEANS_DENOISE

    def enhance_2d(
        self,
        image: np.ndarray,
        h: float = 10.0,
        template_window_size: int = 7,
        search_window_size: int = 21,
        **kwargs: Any,
    ) -> np.ndarray:
        """Apply Non-Local Means denoising to a single 2D slice.

        Args:
            image: 2D float32 array in [0, 1] range.
            h: Filter strength. Higher h removes more noise but also detail.
            template_window_size: Size of the patch comparison window (odd).
            search_window_size: Size of the search area around each pixel (odd).

        Returns:
            Denoised 2D float32 array in [0, 1] range.
        """
        # Convert to uint8 for OpenCV NLM
        img_uint8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)

        denoised_uint8 = cv2.fastNlMeansDenoising(
            img_uint8,
            h=h,
            templateWindowSize=template_window_size,
            searchWindowSize=search_window_size,
        )

        return denoised_uint8.astype(np.float32) / 255.0
