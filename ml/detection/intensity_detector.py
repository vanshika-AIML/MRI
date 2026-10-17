"""Intensity-based abnormality detector for MRI slices.

Uses statistical deviation analysis to flag regions with abnormally high
or low intensity values relative to local or global image statistics.

DISCLAIMER: This is a baseline heuristic detector for development/testing.
It does NOT provide clinically validated abnormality detection.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from ml.detection.base import (
    AbnormalityRegion,
    BaseDetector,
    DetectionConfig,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class IntensityAnomalyDetector(BaseDetector):
    """Detects intensity anomalies using statistical thresholding.

    Identifies regions where local intensity significantly deviates from
    the mean intensity of the image. This can flag hyperintense or
    hypointense regions that may correspond to lesions, edema, or artifacts.

    Limitations:
    - High false-positive rate on normal anatomical variation.
    - No spatial context or learned features; purely statistical.
    - Performance degrades on poorly normalized images.
    - Not trained on any clinical dataset.
    """

    detector_name: str = "intensity_anomaly_detector"

    def detect_2d(
        self,
        image: np.ndarray,
        config: DetectionConfig,
    ) -> List[AbnormalityRegion]:
        """Detect intensity anomalies in a single 2D MRI slice.

        Args:
            image: 2D float32 array in [0, 1] range.
            config: Detection configuration.

        Returns:
            List of AbnormalityRegion objects for detected anomalies.
        """
        params = config.params
        z_threshold = params.get("z_threshold", 2.5)
        min_region_area = params.get("min_region_area", 10)
        detect_hyperintense = params.get("detect_hyperintense", True)
        detect_hypointense = params.get("detect_hypointense", True)

        regions: List[AbnormalityRegion] = []

        # Compute global statistics (ignoring near-zero background)
        foreground_mask = image > 0.05
        if not np.any(foreground_mask):
            return regions

        fg_values = image[foreground_mask]
        mean_val = float(np.mean(fg_values))
        std_val = float(np.std(fg_values))

        if std_val < 1e-8:
            return regions

        # Detect hyperintense regions (bright spots)
        if detect_hyperintense:
            hyper_threshold = mean_val + z_threshold * std_val
            hyper_mask = (image > hyper_threshold) & foreground_mask
            hyper_regions = self._extract_regions(
                image, hyper_mask, "intensity_hyperintense", min_region_area
            )
            regions.extend(hyper_regions)

        # Detect hypointense regions (dark spots within brain)
        if detect_hypointense:
            hypo_threshold = mean_val - z_threshold * std_val
            if hypo_threshold > 0.05:  # Only detect if threshold is above background
                hypo_mask = (image < hypo_threshold) & foreground_mask
                hypo_regions = self._extract_regions(
                    image, hypo_mask, "intensity_hypointense", min_region_area
                )
                regions.extend(hypo_regions)

        return regions

    def _extract_regions(
        self,
        image: np.ndarray,
        binary_mask: np.ndarray,
        label: str,
        min_area: int,
    ) -> List[AbnormalityRegion]:
        """Extract connected components from a binary mask as regions."""
        regions: List[AbnormalityRegion] = []

        mask_uint8 = binary_mask.astype(np.uint8) * 255
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            mask_uint8, connectivity=8
        )

        for comp_id in range(1, num_labels):  # Skip background (0)
            area = int(stats[comp_id, cv2.CC_STAT_AREA])
            if area < min_area:
                continue

            x = int(stats[comp_id, cv2.CC_STAT_LEFT])
            y = int(stats[comp_id, cv2.CC_STAT_TOP])
            w = int(stats[comp_id, cv2.CC_STAT_WIDTH])
            h = int(stats[comp_id, cv2.CC_STAT_HEIGHT])

            # Compute mean intensity in region
            region_mask = labels == comp_id
            region_mean = float(np.mean(image[region_mask]))

            # Confidence based on how far the mean deviates from image mean
            fg_values = image[image > 0.05]
            if len(fg_values) == 0:
                continue
            global_mean = float(np.mean(fg_values))
            global_std = float(np.std(fg_values))
            if global_std < 1e-8:
                continue

            z_score = abs(region_mean - global_mean) / global_std
            confidence = float(np.clip(z_score / 5.0, 0.0, 1.0))

            # Severity based on z-score
            if z_score < 2.0:
                severity = SeverityLevel.NONE
            elif z_score < 3.0:
                severity = SeverityLevel.LOW
            elif z_score < 4.5:
                severity = SeverityLevel.MODERATE
            else:
                severity = SeverityLevel.HIGH

            regions.append(
                AbnormalityRegion(
                    region_id=f"intensity_{uuid.uuid4().hex[:8]}",
                    label=label,
                    confidence=round(confidence, 4),
                    severity=severity,
                    bounding_box=(y, x, y + h, x + w),
                    centroid=(float(centroids[comp_id][1]), float(centroids[comp_id][0])),
                    area_pixels=area,
                    mean_intensity=round(region_mean, 4),
                    metadata={
                        "max_intensity": float(np.max(image[region_mask])),
                        "z_score": round(z_score, 4),
                        "global_mean": round(global_mean, 4),
                        "global_std": round(global_std, 4),
                    },
                )
            )

        return regions
