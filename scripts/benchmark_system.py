"""Reproducible synthetic HTTP concurrency and pipeline timings (not clinical accuracy)."""
import argparse
import concurrent.futures
import io
import json
from pathlib import Path
import statistics
import time
import tracemalloc
import httpx
import numpy as np
from PIL import Image
from ml.evaluation.benchmark_pipeline import run_pipeline_benchmarks

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8002')
parser.add_argument('--output', default='docs/verification/performance.json')
args = parser.parse_args()
tracemalloc.start()
pipeline = run_pipeline_benchmarks()
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
array = np.random.default_rng(42).integers(40, 200, (256, 256), dtype=np.uint8)
stream = io.BytesIO()
Image.fromarray(array).save(stream, format='PNG')
with httpx.Client(base_url=args.base_url, timeout=60) as client:
    def run(_):
        start = time.perf_counter()
        response = client.post('/api/v1/analysis', files={'file': ('synthetic.png', stream.getvalue(), 'image/png')})
        assert response.status_code == 200 and response.json()['success'], response.text
        return (time.perf_counter() - start) * 1000
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        timings = list(pool.map(run, range(16)))
    corrupt = client.post('/api/v1/analysis', files={'file': ('corrupt.npy', b'bad')})
    assert corrupt.status_code == 400
    recovery = run(0)
    health = client.get('/api/v1/health')
    assert health.status_code == 200
output = {'pipeline': pipeline, 'python_tracemalloc_peak_bytes': peak,
    'native_memory_included': False, 'concurrency': 4, 'http_requests': 16,
    'http_p50_ms': statistics.median(timings), 'http_p95_ms': float(np.percentile(timings, 95)),
    'http_max_ms': max(timings), 'malformed_then_valid_recovery': True,
    'health': health.json(), 'limitations': 'Synthetic inputs on this development host; not a production capacity or clinical benchmark.'}
Path(args.output).write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps({k:v for k,v in output.items() if k != 'pipeline'}, indent=2))
