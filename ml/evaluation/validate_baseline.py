"""Seeded synthetic localization baseline; NEVER a clinical validation dataset.

Run from root: python -m ml.evaluation.validate_baseline --output docs/verification/model-baseline.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from ml.inference.pipeline import MRIInferencePipeline
from ml.inference.schemas import InferenceInput


def evaluate():
    rng = np.random.default_rng(42)
    pipeline = MRIInferencePipeline()
    rows = []
    for index in range(20):
        image = rng.normal(0.45, 0.025, (128, 128)).astype(np.float32)
        positive = index % 2 == 0
        truth = np.zeros(image.shape, dtype=bool)
        if positive:
            truth[40:56, 60:76] = True
            image[truth] = 0.95
        result = pipeline.run(image, InferenceInput(normalize=False, enable_enhancement=False))
        assert result.success
        prediction = np.zeros(image.shape, dtype=bool)
        for detection in result.detection_results:
            for region in detection.regions:
                y0, x0, y1, x1 = region.bounding_box
                assert 0 <= y0 < y1 <= 128 and 0 <= x0 < x1 <= 128
                prediction[y0:y1, x0:x1] = True
        denominator = int(prediction.sum() + truth.sum())
        rows.append({"case": index, "positive": positive,
            "sha256": hashlib.sha256(image.tobytes()).hexdigest(),
            "flagged": bool(prediction.any()),
            "bbox_dice": float(2 * (prediction & truth).sum() / denominator) if denominator else 1.0})
    return {"seed": 42, "dataset": "synthetic Gaussian fields with rectangular intensity inserts",
        "clinical_validation": False, "trained_weights": None, "cases": rows,
        "sensitivity_synthetic": sum(r['flagged'] for r in rows if r['positive']) / 10,
        "specificity_synthetic": sum(not r['flagged'] for r in rows if not r['positive']) / 10,
        "mean_bbox_dice": float(np.mean([r['bbox_dice'] for r in rows])),
        "limitations": ["Bounding-box overlap is not lesion segmentation accuracy.",
            "No patient data, scanner diversity, labeled clinical cohort, or trained checkpoint is present.",
            "Default CLAHE/normalization are covered by pipeline tests, not this detector-isolation benchmark.",
            "3D processing is slice-wise along the last axis; no anatomical registration or lesion classification."]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evaluate(), indent=2) + '\n')
