"""Texture-based abnormality detector for MRI slices.

Uses local variance / texture heterogeneity analysis to identify regions
where tissue texture deviates significantly from the surrounding context,
which may indicate pathology, artifacts, or structural anomalies.

DISCLAIMER: This is a baseline heuristic detector for development/testing.
It does NOT provide clinically validated abnormality detection.
"""

import logging
import uuid
from typing import Any, Dict, List

import cv2
import numpy as np
from scipy.ndimage import uniform_filter

from ml.detection.base import (
    AbnormalityRegion,
    BaseDetector,
    DetectionConfig,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class TextureAnomalyDetector(BaseDetector):
    """Detects texture anomalies using local variance analysis.

    Computes local intensity variance within a sliding window and flags
    regions where variance is abnormally high or low compared to the
    image-wide distribution.

    Limitations:
    - Sensitive to window size selection and noise level.
    - No learned feature representations; uses hand-crafted statistics.
    - May produce false positives at tissue boundaries (gray/white matter).
    - Not validated against any clinical reference standard.
    """

    detector_name: str = "texture_anomaly_detector"

    def detect_2d(
        self,
        image: np.ndarray,
        config: DetectionConfig,
    ) -> List[AbnormalityRegion]:
        """Detect texture anomalies in a single 2D MRI slice.

        Args:
            image: 2D float32 array in [0, 1] range.
            config: Detection configuration.

        Returns:
            List of AbnormalityRegion objects for detected texture anomalies.
        """
        params = config.params
        window_size = params.get("window_size", 9)
        variance_z_threshold = params.get("variance_z_threshold", 3.0)
        min_region_area = params.get("min_region_area", 15)

        regions: List[AbnormalityRegion] = []

        # Foreground mask: ignore background
        foreground_mask = image > 0.05
        if not np.any(foreground_mask):
            return regions

        # Compute local variance map
        local_mean = uniform_filter(image.astype(np.float64), size=window_size)
        local_sq_mean = uniform_filter(
            (image.astype(np.float64)) ** 2, size=window_size
        )
        local_variance = np.maximum(local_sq_mean - local_mean**2, 0.0).astype(np.float32)

        # Compute statistics on foreground variance
        fg_variance = local_variance[foreground_mask]
        var_mean = float(np.mean(fg_variance))
        var_std = float(np.std(fg_variance))

        if var_std < 1e-10:
            return regions

        # Threshold for abnormally high local variance
        var_threshold = var_mean + variance_z_threshold * var_std
        anomaly_mask = (local_variance > var_threshold) & foreground_mask

        # Extract connected components
        mask_uint8 = anomaly_mask.astype(np.uint8) * 255
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            mask_uint8, connectivity=8
        )

        for comp_id in range(1, num_labels):
            area = int(stats[comp_id, cv2.CC_STAT_AREA])
            if area < min_region_area:
                continue

            x = int(stats[comp_id, cv2.CC_STAT_LEFT])
            y = int(stats[comp_id, cv2.CC_STAT_TOP])
            w = int(stats[comp_id, cv2.CC_STAT_WIDTH])
            h = int(stats[comp_id, cv2.CC_STAT_HEIGHT])

            region_mask = labels == comp_id
            region_mean_var = float(np.mean(local_variance[region_mask]))
            region_mean_intensity = float(np.mean(image[region_mask]))

            # Confidence: how far the region variance exceeds the threshold
            z_score = (region_mean_var - var_mean) / var_std
            confidence = float(np.clip(z_score / 6.0, 0.0, 1.0))

            if z_score < 2.0:
                severity = SeverityLevel.NONE
            elif z_score < 3.5:
                severity = SeverityLevel.LOW
            elif z_score < 5.0:
                severity = SeverityLevel.MODERATE
            else:
                severity = SeverityLevel.HIGH

            regions.append(
                AbnormalityRegion(
                    region_id=f"texture_{uuid.uuid4().hex[:8]}",
                    label="texture_anomaly",
                    confidence=round(confidence, 4),
                    severity=severity,
                    bounding_box=(y, x, y + h, x + w),
                    centroid=(float(centroids[comp_id][1]), float(centroids[comp_id][0])),
                    area_pixels=area,
                    mean_intensity=round(region_mean_intensity, 4),
                    metadata={
                        "variance_z_score": round(z_score, 4),
                        "region_mean_variance": round(region_mean_var, 6),
                        "global_variance_mean": round(var_mean, 6),
                        "global_variance_std": round(var_std, 6),
                    },
                )
            )

        return regions
