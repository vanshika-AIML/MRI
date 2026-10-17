"""Unit tests for MRI image enhancement modules.

Tests CLAHE, histogram equalization, Gaussian denoising, non-local means
denoising, and unsharp mask sharpening on synthetic 2D slices and 3D volumes.
"""

import numpy as np
import pytest

from ml.enhancement.base import BaseEnhancer, EnhancementMethod, EnhancementResult
from ml.enhancement.contrast import CLAHEEnhancer, HistogramEqualizationEnhancer
from ml.enhancement.denoise import GaussianDenoiser, NonLocalMeansDenoiser
from ml.enhancement.sharpening import UnsharpMaskEnhancer


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def sample_2d_image() -> np.ndarray:
    """Create a synthetic 2D MRI-like slice in [0, 1] range."""
    np.random.seed(42)
    img = np.zeros((64, 64), dtype=np.float32)
    # Simulated brain region
    img[10:54, 10:54] = 0.5
    img[20:44, 20:44] = 0.7
    # Add noise
    img += np.random.normal(0, 0.02, img.shape).astype(np.float32)
    return np.clip(img, 0.0, 1.0)


@pytest.fixture
def sample_3d_volume() -> np.ndarray:
    """Create a synthetic 3D MRI-like volume in [0, 1] range."""
    np.random.seed(42)
    vol = np.zeros((32, 32, 8), dtype=np.float32)
    vol[5:27, 5:27, 2:6] = 0.6
    vol[10:22, 10:22, 3:5] = 0.8
    vol += np.random.normal(0, 0.02, vol.shape).astype(np.float32)
    return np.clip(vol, 0.0, 1.0)


@pytest.fixture
def uniform_image() -> np.ndarray:
    """Uniform intensity image (edge case)."""
    return np.full((32, 32), 0.5, dtype=np.float32)


# ── CLAHE Tests ──────────────────────────────────────────────────────


class TestCLAHEEnhancer:
    """Tests for CLAHE contrast enhancement."""

    def test_clahe_2d_output_shape(self, sample_2d_image):
        """CLAHE output should match input shape."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(sample_2d_image)
        assert result.success
        assert result.output_shape == sample_2d_image.shape

    def test_clahe_2d_output_range(self, sample_2d_image):
        """CLAHE output should be in [0, 1] range."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(sample_2d_image)
        enhanced = result._enhanced_array
        assert enhanced.min() >= 0.0
        assert enhanced.max() <= 1.0

    def test_clahe_changes_image(self, sample_2d_image):
        """CLAHE should modify the image (not be a no-op)."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(sample_2d_image)
        enhanced = result._enhanced_array
        assert not np.allclose(enhanced, sample_2d_image, atol=1e-3)

    def test_clahe_method_identifier(self):
        """CLAHE should report correct method enum."""
        enhancer = CLAHEEnhancer()
        assert enhancer.method == EnhancementMethod.CLAHE

    def test_clahe_custom_params(self, sample_2d_image):
        """CLAHE should accept custom clip_limit and tile_grid_size."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(sample_2d_image, clip_limit=4.0, tile_grid_size=4)
        assert result.success
        assert result._enhanced_array.shape == sample_2d_image.shape

    def test_clahe_3d_volume(self, sample_3d_volume):
        """CLAHE should work on 3D volumes (slice-by-slice)."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(sample_3d_volume)
        assert result.success
        assert result.output_shape == sample_3d_volume.shape


# ── Histogram Equalization Tests ─────────────────────────────────────


class TestHistogramEqualizationEnhancer:
    """Tests for global histogram equalization."""

    def test_histeq_2d_output_shape(self, sample_2d_image):
        enhancer = HistogramEqualizationEnhancer()
        result = enhancer.enhance(sample_2d_image)
        assert result.success
        assert result.output_shape == sample_2d_image.shape

    def test_histeq_2d_output_range(self, sample_2d_image):
        enhancer = HistogramEqualizationEnhancer()
        result = enhancer.enhance(sample_2d_image)
        enhanced = result._enhanced_array
        assert enhanced.min() >= 0.0
        assert enhanced.max() <= 1.0

    def test_histeq_method_identifier(self):
        enhancer = HistogramEqualizationEnhancer()
        assert enhancer.method == EnhancementMethod.HISTOGRAM_EQUALIZATION


# ── Gaussian Denoiser Tests ──────────────────────────────────────────


class TestGaussianDenoiser:
    """Tests for Gaussian blur denoising."""

    def test_gaussian_2d_output_shape(self, sample_2d_image):
        denoiser = GaussianDenoiser()
        result = denoiser.enhance(sample_2d_image)
        assert result.success
        assert result.output_shape == sample_2d_image.shape

    def test_gaussian_reduces_noise(self):
        """Gaussian denoising should reduce high-frequency noise variance."""
        np.random.seed(99)
        clean = np.full((64, 64), 0.5, dtype=np.float32)
        noisy = clean + np.random.normal(0, 0.1, clean.shape).astype(np.float32)
        noisy = np.clip(noisy, 0.0, 1.0)

        denoiser = GaussianDenoiser()
        result = denoiser.enhance(noisy, kernel_size=5, sigma=1.5)
        denoised = result._enhanced_array

        # Denoised should be closer to the clean image
        noise_before = float(np.std(noisy - clean))
        noise_after = float(np.std(denoised - clean))
        assert noise_after < noise_before

    def test_gaussian_even_kernel_handled(self, sample_2d_image):
        """Even kernel sizes should be auto-corrected to odd."""
        denoiser = GaussianDenoiser()
        result = denoiser.enhance(sample_2d_image, kernel_size=4)
        assert result.success

    def test_gaussian_3d_volume(self, sample_3d_volume):
        denoiser = GaussianDenoiser()
        result = denoiser.enhance(sample_3d_volume)
        assert result.success
        assert result.output_shape == sample_3d_volume.shape


# ── Non-Local Means Denoiser Tests ───────────────────────────────────


class TestNonLocalMeansDenoiser:
    """Tests for Non-Local Means denoising."""

    def test_nlm_2d_output_shape(self, sample_2d_image):
        denoiser = NonLocalMeansDenoiser()
        result = denoiser.enhance(sample_2d_image)
        assert result.success
        assert result.output_shape == sample_2d_image.shape

    def test_nlm_2d_output_range(self, sample_2d_image):
        denoiser = NonLocalMeansDenoiser()
        result = denoiser.enhance(sample_2d_image)
        enhanced = result._enhanced_array
        assert enhanced.min() >= 0.0
        assert enhanced.max() <= 1.0


# ── Unsharp Mask Enhancer Tests ──────────────────────────────────────


class TestUnsharpMaskEnhancer:
    """Tests for unsharp mask sharpening."""

    def test_unsharp_2d_output_shape(self, sample_2d_image):
        enhancer = UnsharpMaskEnhancer()
        result = enhancer.enhance(sample_2d_image)
        assert result.success
        assert result.output_shape == sample_2d_image.shape

    def test_unsharp_2d_output_range(self, sample_2d_image):
        enhancer = UnsharpMaskEnhancer()
        result = enhancer.enhance(sample_2d_image)
        enhanced = result._enhanced_array
        assert enhanced.min() >= 0.0
        assert enhanced.max() <= 1.0

    def test_unsharp_method_identifier(self):
        enhancer = UnsharpMaskEnhancer()
        assert enhancer.method == EnhancementMethod.UNSHARP_MASK

    def test_unsharp_custom_strength(self, sample_2d_image):
        enhancer = UnsharpMaskEnhancer()
        result = enhancer.enhance(sample_2d_image, sigma=2.0, strength=3.0)
        assert result.success


# ── Base Enhancer / Edge Case Tests ──────────────────────────────────


class TestBaseEnhancerEdgeCases:
    """Edge cases and error handling for the base enhancer interface."""

    def test_invalid_input_type(self):
        """Non-ndarray input should produce a failed result."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance("not_an_array")
        assert not result.success
        assert result.error_message is not None

    def test_empty_array(self):
        """Empty array should produce a failed result."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(np.array([], dtype=np.float32))
        assert not result.success

    def test_1d_array_rejected(self):
        """1D array should produce a failed result."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(np.array([1.0, 2.0, 3.0], dtype=np.float32))
        assert not result.success

    def test_4d_array_rejected(self):
        """4D array should produce a failed result."""
        enhancer = CLAHEEnhancer()
        arr_4d = np.random.rand(8, 8, 8, 3).astype(np.float32)
        result = enhancer.enhance(arr_4d)
        assert not result.success

    def test_uniform_image_no_crash(self, uniform_image):
        """Uniform intensity image should not crash any enhancer."""
        for enhancer_cls in [
            CLAHEEnhancer,
            HistogramEqualizationEnhancer,
            GaussianDenoiser,
            UnsharpMaskEnhancer,
        ]:
            enhancer = enhancer_cls()
            result = enhancer.enhance(uniform_image)
            assert result.success, f"{enhancer_cls.__name__} failed on uniform image"

    def test_result_metadata_populated(self, sample_2d_image):
        """EnhancementResult should have all metadata fields populated."""
        enhancer = CLAHEEnhancer()
        result = enhancer.enhance(sample_2d_image, clip_limit=3.0)

        assert result.method == EnhancementMethod.CLAHE
        assert result.input_shape == (64, 64)
        assert result.output_shape == (64, 64)
        assert len(result.input_intensity_range) == 2
        assert len(result.output_intensity_range) == 2
        assert result.success is True
        assert result.error_message is None
