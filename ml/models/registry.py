"""Model Registry for MRI enhancement and detection models.

Provides a central registry that decouples model instantiation and
configuration from inference pipeline logic. Models are registered
by name and can be retrieved at inference time.

This design allows:
- Swapping baseline heuristic models with trained deep learning models.
- Registering multiple models for A/B comparison.
- Lazy loading of heavy model weights.
- Environment-specific model configurations.
"""

import logging
from typing import Dict, Optional

from ml.detection.base import BaseDetector
from ml.enhancement.base import BaseEnhancer

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Central registry for MRI analysis models.

    Stores named enhancer and detector instances. The inference pipeline
    queries this registry to resolve model names to concrete implementations.

    Usage:
        registry = ModelRegistry()
        registry.register_enhancer("clahe", CLAHEEnhancer())
        registry.register_detector("intensity_anomaly", IntensityAnomalyDetector())

        # Or use the default factory:
        registry = ModelRegistry.create_default()
    """

    def __init__(self) -> None:
        """Initialize an empty model registry."""
        self._enhancers: Dict[str, BaseEnhancer] = {}
        self._detectors: Dict[str, BaseDetector] = {}

    # ── Enhancer management ──────────────────────────────────────────

    def register_enhancer(self, name: str, enhancer: BaseEnhancer) -> None:
        """Register an enhancer instance under a given name.

        Args:
            name: Unique name for the enhancer (e.g., 'clahe', 'nlm_denoise').
            enhancer: BaseEnhancer subclass instance.
        """
        if not isinstance(enhancer, BaseEnhancer):
            raise TypeError(
                f"Expected BaseEnhancer instance, got {type(enhancer).__name__}"
            )
        self._enhancers[name] = enhancer
        logger.info(f"Registered enhancer: '{name}' ({type(enhancer).__name__})")

    def get_enhancer(self, name: str) -> Optional[BaseEnhancer]:
        """Retrieve a registered enhancer by name.

        Args:
            name: Name of the enhancer to retrieve.

        Returns:
            BaseEnhancer instance, or None if not found.
        """
        aliases = {"gaussian": "gaussian_denoise", "histeq": "histogram_equalization", "unsharp": "unsharp_mask"}
        return self._enhancers.get(aliases.get(name, name))

    def list_enhancers(self) -> list:
        """List all registered enhancer names."""
        return list(self._enhancers.keys())

    # ── Detector management ──────────────────────────────────────────

    def register_detector(self, name: str, detector: BaseDetector) -> None:
        """Register a detector instance under a given name.

        Args:
            name: Unique name for the detector (e.g., 'intensity_anomaly').
            detector: BaseDetector subclass instance.
        """
        if not isinstance(detector, BaseDetector):
            raise TypeError(
                f"Expected BaseDetector instance, got {type(detector).__name__}"
            )
        self._detectors[name] = detector
        logger.info(f"Registered detector: '{name}' ({type(detector).__name__})")

    def get_detector(self, name: str) -> Optional[BaseDetector]:
        """Retrieve a registered detector by name.

        Args:
            name: Name of the detector to retrieve.

        Returns:
            BaseDetector instance, or None if not found.
        """
        return self._detectors.get(name)

    def list_detectors(self) -> list:
        """List all registered detector names."""
        return list(self._detectors.keys())

    # ── Factory ──────────────────────────────────────────────────────

    @classmethod
    def create_default(cls) -> "ModelRegistry":
        """Create a registry pre-loaded with all baseline models.

        Returns:
            ModelRegistry with baseline enhancers and detectors registered.
        """
        from ml.detection.intensity_detector import IntensityAnomalyDetector
        from ml.detection.texture_detector import TextureAnomalyDetector
        from ml.enhancement.contrast import CLAHEEnhancer, HistogramEqualizationEnhancer
        from ml.enhancement.denoise import GaussianDenoiser, NonLocalMeansDenoiser
        from ml.enhancement.sharpening import UnsharpMaskEnhancer

        registry = cls()

        # Register baseline enhancers
        registry.register_enhancer("clahe", CLAHEEnhancer())
        registry.register_enhancer("histogram_equalization", HistogramEqualizationEnhancer())
        registry.register_enhancer("gaussian_denoise", GaussianDenoiser())
        registry.register_enhancer("non_local_means_denoise", NonLocalMeansDenoiser())
        registry.register_enhancer("unsharp_mask", UnsharpMaskEnhancer())

        # Register baseline detectors
        registry.register_detector("intensity_anomaly", IntensityAnomalyDetector())
        registry.register_detector("texture_anomaly", TextureAnomalyDetector())

        logger.info(
            f"Default registry created: {len(registry._enhancers)} enhancers, "
            f"{len(registry._detectors)} detectors"
        )
        return registry

    def __repr__(self) -> str:
        return (
            f"ModelRegistry(enhancers={self.list_enhancers()}, "
            f"detectors={self.list_detectors()})"
        )
