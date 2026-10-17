"""Unit tests for MRI intensity transforms, masking, and resampling."""

import numpy as np
import pytest

from ml.preprocessing.transforms import (
    normalize_intensity_zscore,
    normalize_intensity_minmax,
    apply_windowing,
    percentile_clipping,
    resample_volume,
    create_brain_mask_otsu,
    n4_bias_field_correction,
)


def test_normalize_intensity_zscore():
    """Test Z-score zero mean and unit variance normalization."""
    arr = np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float32)
    norm = normalize_intensity_zscore(arr)

    assert pytest.approx(float(np.mean(norm)), abs=1e-5) == 0.0
    assert pytest.approx(float(np.std(norm)), abs=1e-5) == 1.0


def test_normalize_intensity_zscore_with_mask():
    """Test Z-score normalization with background mask."""
    arr = np.array([0.0, 0.0, 10.0, 20.0, 30.0], dtype=np.float32)
    mask = np.array([False, False, True, True, True])

    norm = normalize_intensity_zscore(arr, mask=mask)
    assert norm[0] == 0.0
    assert norm[1] == 0.0
    assert pytest.approx(float(np.mean(norm[mask])), abs=1e-5) == 0.0


def test_normalize_intensity_minmax():
    """Test Min-Max scaling to [0.0, 1.0]."""
    arr = np.array([10.0, 25.0, 50.0, 75.0, 100.0], dtype=np.float32)
    scaled = normalize_intensity_minmax(arr, min_val=0.0, max_val=1.0, clip_percentiles=None)

    assert scaled.min() == 0.0
    assert scaled.max() == 1.0


def test_apply_windowing():
    """Test window center / window width clipping and scaling."""
    arr = np.array([0.0, 200.0, 400.0, 600.0, 800.0], dtype=np.float32)
    windowed = apply_windowing(arr, window_center=400.0, window_width=400.0)

    # Window range: 200 to 600
    assert windowed[0] == 0.0  # 0 < 200 -> clipped to 200 -> 0.0
    assert windowed[1] == 0.0  # 200 -> 0.0
    assert windowed[2] == 0.5  # 400 -> 0.5
    assert windowed[3] == 1.0  # 600 -> 1.0
    assert windowed[4] == 1.0  # 800 > 600 -> clipped to 600 -> 1.0


def test_percentile_clipping():
    """Test extreme value percentile clipping."""
    arr = np.arange(100, dtype=np.float32)
    clipped = percentile_clipping(arr, lower=5.0, upper=95.0)

    assert clipped.min() >= 4.0
    assert clipped.max() <= 96.0


def test_resample_volume():
    """Test 3D volume resampling from (2.0, 2.0, 2.0) mm to (1.0, 1.0, 1.0) mm spacing."""
    vol = np.random.rand(10, 10, 10).astype(np.float32)
    resampled, target_spacing = resample_volume(
        vol,
        current_spacing=(2.0, 2.0, 2.0),
        target_spacing=(1.0, 1.0, 1.0),
        order=1,
    )

    assert resampled.shape == (20, 20, 20)
    assert target_spacing == (1.0, 1.0, 1.0)


def test_create_brain_mask_otsu():
    """Test background threshold brain mask generation."""
    img = np.zeros((32, 32), dtype=np.float32)
    img[8:24, 8:24] = 500.0  # High intensity brain square

    mask = create_brain_mask_otsu(img)
    assert mask.shape == (32, 32)
    assert mask.dtype == bool
    assert np.all(mask[10:22, 10:22])
    assert not np.any(mask[0:5, 0:5])


def test_n4_bias_field_correction():
    """Test N4 bias field correction on synthetic 3D volume."""
    vol = np.ones((16, 16, 16), dtype=np.float32) * 200.0
    corrected = n4_bias_field_correction(vol)

    assert corrected.shape == (16, 16, 16)
    assert not np.isnan(corrected).any()
