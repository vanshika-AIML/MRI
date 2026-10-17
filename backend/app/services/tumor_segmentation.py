"""Lazy, process-local loader for the opt-in research FLAIR segmenter."""
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from ml.inference.tumor_segmenter import TumorModelConfigurationError, TumorSegmenter


@lru_cache(maxsize=2)
def _load_segmenter(run_directory: str) -> TumorSegmenter:
    return TumorSegmenter(Path(run_directory))


def get_tumor_segmenter() -> TumorSegmenter:
    if not settings.MRI_TUMOR_MODEL_RUN_DIR:
        raise FileNotFoundError("Research segmentation model is not configured")
    return _load_segmenter(settings.MRI_TUMOR_MODEL_RUN_DIR)
