"""MRI Intensity Normalization, Filtering, Masking, and Resampling Transforms.

Provides standard pre-processing transformations for 2D slices and 3D medical volumes.
"""

import logging
from typing import Optional, Tuple, Union

import numpy as np
from scipy.ndimage import zoom

logger = logging.getLogger(__name__)


def normalize_intensity_zscore(
    image: np.ndarray,
    mask: Optional[np.ndarray] = None,
    eps: float = 1e-8,
) -> np.ndarray:
    """Normalize intensity values to zero mean and unit variance (Z-score).

    If a mask is provided (e.g. brain mask), mean and std are computed only on foreground.
    """
    image_float = image.astype(np.float32)

    if mask is not None and np.any(mask):
        fg_values = image_float[mask > 0]
        mean = float(np.mean(fg_values))
        std = float(np.std(fg_values))
    else:
        mean = float(np.mean(image_float))
        std = float(np.std(image_float))

    std = max(std, eps)
    normalized = (image_float - mean) / std

    if mask is not None:
        normalized[mask == 0] = 0.0

    return normalized


def normalize_intensity_minmax(
    image: np.ndarray,
    min_val: float = 0.0,
    max_val: float = 1.0,
    clip_percentiles: Optional[Tuple[float, float]] = (1.0, 99.0),
) -> np.ndarray:
    """Min-Max scale intensity values to range [min_val, max_val].

    Optionally clips extreme outliers using percentiles before scaling.
    """
    img = image.astype(np.float32)

    if clip_percentiles is not None:
        low_p, high_p = clip_percentiles
        low_v, high_v = np.percentile(img, (low_p, high_p))
        if high_v > low_v:
            img = np.clip(img, low_v, high_v)

    img_min = float(np.min(img))
    img_max = float(np.max(img))

    if img_max > img_min:
        scaled = (img - img_min) / (img_max - img_min)
        scaled = scaled * (max_val - min_val) + min_val
    else:
        scaled = np.zeros_like(img) + min_val

    return scaled


def apply_windowing(
    image: np.ndarray,
    window_center: float,
    window_width: float,
) -> np.ndarray:
    """Apply Hounsfield / MRI contrast windowing."""
    if window_width <= 0:
        return image.astype(np.float32)

    min_val = window_center - (window_width / 2.0)
    max_val = window_center + (window_width / 2.0)

    clipped = np.clip(image.astype(np.float32), min_val, max_val)
    normalized = (clipped - min_val) / window_width
    return normalized


def percentile_clipping(
    image: np.ndarray,
    lower: float = 1.0,
    upper: float = 99.0,
) -> np.ndarray:
    """Clip image intensity values between lower and upper percentiles."""
    img = image.astype(np.float32)
    low_v, high_v = np.percentile(img, (lower, upper))
    return np.clip(img, low_v, high_v)


def resample_volume(
    volume: np.ndarray,
    current_spacing: Tuple[float, float, float],
    target_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    order: int = 1,
) -> Tuple[np.ndarray, Tuple[float, float, float]]:
    """Resample a 3D medical volume to target isotropic/anisotropic voxel spacing.

    Args:
        volume: 3D numpy array (depth, height, width) or (x, y, z).
        current_spacing: Tuple of spacing in mm for each axis.
        target_spacing: Tuple of desired spacing in mm for each axis.
        order: Interpolation order (0 = nearest, 1 = bilinear/trilinear, 3 = cubic).

    Returns:
        Tuple of (resampled 3D numpy array, target_spacing).
    """
    zoom_factors = [curr / targ for curr, targ in zip(current_spacing, target_spacing)]
    resampled = zoom(volume.astype(np.float32), zoom=zoom_factors, order=order)
    return resampled, target_spacing


def create_brain_mask_otsu(image: np.ndarray) -> np.ndarray:
    """Simple background thresholding / Otsu-like mask for brain MRIs.

    Returns binary boolean mask where True = foreground (brain/tissue), False = background air.
    """
    img = image.astype(np.float32)
    bg_thresh = np.percentile(img, 15)
    fg_thresh = np.percentile(img, 85)

    if fg_thresh > bg_thresh:
        thresh = bg_thresh + 0.15 * (fg_thresh - bg_thresh)
    else:
        thresh = np.mean(img)

    mask = img > thresh
    return mask.astype(bool)


def n4_bias_field_correction(volume_3d: np.ndarray) -> np.ndarray:
    """Apply N4 Bias Field Correction using SimpleITK if possible.

    Falls back to high-pass Gaussian filtering if SimpleITK fails.
    """
    try:
        import SimpleITK as sitk

        sitk_img = sitk.GetImageFromArray(volume_3d.astype(np.float32))
        mask_img = sitk.OtsuThreshold(sitk_img, 0, 1, 200)

        corrector = sitk.N4BiasFieldCorrectionImageFilter()
        corrector.SetMaximumNumberOfIterations([50, 50, 30])
        corrected_img = corrector.Execute(sitk_img, mask_img)

        return sitk.GetArrayFromImage(corrected_img)
    except Exception as e:
        logger.warning(f"SimpleITK N4 bias correction fallback due to: {e}")
        # Fallback: estimate low frequency field with heavy Gaussian filter
        from scipy.ndimage import gaussian_filter

        low_pass = gaussian_filter(volume_3d.astype(np.float32), sigma=10)
        low_pass = np.maximum(low_pass, 1e-5)
        corrected = volume_3d / low_pass
        return corrected.astype(np.float32)
