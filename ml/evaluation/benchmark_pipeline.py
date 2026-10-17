"""Performance and latency benchmark suite for MRI processing pipeline.

Measures preprocessing, enhancement, detection, and end-to-end pipeline latency
across 2D slices and 3D volumes to establish baseline performance metrics.
"""

import time
import numpy as np
from typing import Dict, Any

from ml.inference.pipeline import MRIInferencePipeline
from ml.inference.schemas import InferenceInput
from ml.enhancement.contrast import CLAHEEnhancer
from ml.enhancement.denoise import GaussianDenoiser
from ml.detection.intensity_detector import IntensityAnomalyDetector
from ml.detection.texture_detector import TextureAnomalyDetector


def benchmark_component(name: str, fn, iterations: int = 20) -> Dict[str, float]:
    """Execute a function repeatedly and compute timing percentiles."""
    times = []
    # Warmup
    fn()
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)  # ms

    arr = np.array(times)
    return {
        "name": name,
        "mean_ms": float(np.mean(arr)),
        "std_ms": float(np.std(arr)),
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "min_ms": float(np.min(arr)),
        "max_ms": float(np.max(arr)),
        "iterations": iterations,
    }


def run_pipeline_benchmarks() -> Dict[str, Any]:
    """Run comprehensive performance benchmarks across 2D and 3D inputs."""
    pipeline = MRIInferencePipeline()
    clahe = CLAHEEnhancer()
    denoiser = GaussianDenoiser()
    intensity_det = IntensityAnomalyDetector()
    texture_det = TextureAnomalyDetector()

    # Synthetic 2D slice (256x256)
    np.random.seed(42)
    slice_2d = np.random.uniform(20.0, 200.0, (256, 256)).astype(np.float32)

    # Synthetic 3D volume (128x128x16)
    vol_3d = np.random.uniform(20.0, 200.0, (128, 128, 16)).astype(np.float32)

    cfg_2d = InferenceInput(enable_enhancement=True, enable_detection=True)
    cfg_3d = InferenceInput(enable_enhancement=True, enable_detection=True)

    results = {}

    # 1. 2D Component Benchmarks
    results["clahe_2d"] = benchmark_component("CLAHE 2D (256x256)", lambda: clahe.enhance(slice_2d))
    results["denoise_2d"] = benchmark_component("Gaussian Denoise 2D (256x256)", lambda: denoiser.enhance(slice_2d))
    results["intensity_2d"] = benchmark_component("Intensity Detector 2D (256x256)", lambda: intensity_det.detect(slice_2d))
    results["texture_2d"] = benchmark_component("Texture Detector 2D (256x256)", lambda: texture_det.detect(slice_2d), iterations=10)

    # 2. End-to-end 2D Pipeline
    results["full_pipeline_2d"] = benchmark_component(
        "Full Pipeline 2D (256x256)",
        lambda: pipeline.run(slice_2d, config=cfg_2d),
        iterations=15,
    )

    # 3. 3D Volume Benchmarks
    results["clahe_3d"] = benchmark_component("CLAHE 3D (128x128x16)", lambda: clahe.enhance(vol_3d), iterations=5)
    results["full_pipeline_3d"] = benchmark_component(
        "Full Pipeline 3D (128x128x16)",
        lambda: pipeline.run(vol_3d, config=cfg_3d),
        iterations=5,
    )

    return results


if __name__ == "__main__":
    print("Running MRI Pipeline Latency Benchmarks...")
    benchmark_results = run_pipeline_benchmarks()
    print("\n" + "=" * 70)
    print(f"{'Component':<35} | {'Mean (ms)':<10} | {'p95 (ms)':<10} | {'Min (ms)':<8}")
    print("=" * 70)
    for key, data in benchmark_results.items():
        print(f"{data['name']:<35} | {data['mean_ms']:<10.2f} | {data['p95_ms']:<10.2f} | {data['min_ms']:<8.2f}")
    print("=" * 70)
