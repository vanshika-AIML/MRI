"""Model Registry and Configuration.

Provides a central registry for loading, storing, and retrieving enhancement
and detection model instances. Separates model management from inference logic.

Real trained models (PyTorch, ONNX, etc.) can be registered alongside baseline
heuristic models using the same interface.
"""

from ml.models.registry import ModelRegistry

__all__ = ["ModelRegistry"]
