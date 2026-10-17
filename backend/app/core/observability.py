"""Bounded, process-local telemetry without patient or authentication data."""
import time
import uuid
from fastapi import Request

started = time.monotonic()
requests = 0
failures = 0
duration_seconds = 0.0


async def observe(request: Request, call_next):
    global requests, failures, duration_seconds
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    requests += 1
    failures += int(response.status_code >= 500)
    duration_seconds += elapsed
    response.headers['X-Request-ID'] = uuid.uuid4().hex
    response.headers['Server-Timing'] = f'app;dur={elapsed * 1000:.2f}'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if '/auth/' in request.url.path or '/analysis' in request.url.path:
        response.headers['Cache-Control'] = 'no-store'
    return response


def metrics():
    return (f'mri_requests_total {requests}\n'
            f'mri_server_errors_total {failures}\n'
            f'mri_request_duration_seconds_sum {duration_seconds:.6f}\n'
            f'mri_uptime_seconds {time.monotonic() - started:.3f}\n')
