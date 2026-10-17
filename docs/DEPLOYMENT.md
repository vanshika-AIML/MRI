# Reproducible local research deployment

This is a research baseline, not a clinically validated medical device. Use synthetic or appropriately authorized data. Production release remains conditional on the gates in `verification/RELEASE_REPORT.md`.

## Start and verify

1. Start Docker Desktop with its Linux engine.
2. Set a persistent random `SECRET_KEY` in your deployment environment. A missing key is tolerated only in development and invalidates tokens at restart. Never commit the key.
3. From the root: `docker compose --profile full-stack up -d --build`.
4. Open `http://127.0.0.1:5173`. API: `http://127.0.0.1:8000`. PostgreSQL is bound to local port 55433.
5. Verify `docker compose ps`, `/api/v1/ready` (503 if the DB is down), and `/api/v1/metrics`.

Container startup applies versioned migrations before starting the API. Backend runs as a non-root user, one worker. Python runtime dependencies are pinned in `backend/requirements.lock`; web packages use `npm ci` and `package-lock.json`. Source and build contexts exclude virtual environments, secrets, datasets, and build output. Original databases/volumes are preserved.

For native development, create a Python 3.14 virtual environment and install `backend/requirements.lock`. Set `PYTHONPATH` to both the root and `backend`, `DEBUG=false`, and `DATABASE_URL` to the desired local database. Run Alembic from `backend` before starting Uvicorn. Optional training dependencies in `ml/training/requirements.txt` are only for offline research training and are not required by the heuristic inference server; see the [training guide](../ml/training/README.md).

## Optional trained-model inference

The default API image intentionally excludes PyTorch and model weights. To opt into the experimental FLAIR segmenter, point the overlay at a locally verified run directory containing `weights.pt` and `evaluation.json`, then build the optional CPU runtime:

```powershell
$env:MRI_TUMOR_MODEL_HOST_RUN_DIR = (Resolve-Path .\ml\runs\msd-flair-pilot).Path
docker compose -f docker-compose.yml -f docker-compose.research.yml --profile full-stack up -d --build
```

The run directory is mounted read-only; no checkpoint is baked into the image. The optional overlay installs the separately pinned research training dependencies, so the image is materially larger. The full local stack (database, API and web) was built and started with the overlay; all services became healthy. Authenticated synthetic FLAIR inference, owner-scoped report retrieval, and report recovery after API and database container restarts passed. The browser and Android emulator also completed the research workflow. See the [integrated deployment evidence](./verification/phase18-22-integrated-deployment.json). These are local engineering checks, not production deployment or clinical validation.

Calls to `POST /api/v1/analysis` with `analysis_method=research_flair_segmentation` require a signed-in account, a reachable database, and a 3D FLAIR NIfTI volume. Model/checkpoint or inference errors are explicit and never fall back to heuristics. Do not use this experimental path for clinical decisions. Omit the overlay to retain the lightweight baseline-only deployment. The local Nginx CSP currently permits the default API at `127.0.0.1:8000` and `localhost:8000`; adjust the CSP to the actual API origin when building for another host. HSTS is not set by this HTTP-only local stack and must be configured at the TLS-terminating production proxy.

To stage a custom candidate, train into a new immutable run directory and review its saved manifest/evaluation, split, metrics, provenance and checkpoint hash. Before switching, load the checkpoint in the optional image with a read-only mount to catch missing, mismatched or unloadable artifacts:

```powershell
$env:MRI_TUMOR_MODEL_HOST_RUN_DIR = (Resolve-Path .\ml\runs\candidate-run).Path
docker run --rm --mount "type=bind,source=$env:MRI_TUMOR_MODEL_HOST_RUN_DIR,target=/opt/mri-model,readonly" --workdir /opt/mri-model --entrypoint python mri-backend:latest -c "from pathlib import Path; from ml.inference.tumor_segmenter import TumorSegmenter; TumorSegmenter(Path.cwd())"
```

Do not change the active Compose mount unless that preflight exits successfully. Record the previous immutable run path and keep both runs intact. Promote by setting `MRI_TUMOR_MODEL_HOST_RUN_DIR` to the candidate and recreating the backend; roll back by restoring the recorded previous path and recreating it. The Phase 18 check confirmed an incomplete candidate fails preflight without changing the active container or mount. Promotion/rollback are explicit research configuration switches, not an automated registry or clinical promotion gate.

## Backups and recovery

Run `powershell -File scripts/backup-database.ps1`. It creates a PostgreSQL custom-format dump in ignored `.backups/` and prints its SHA256. Treat dumps as sensitive; encrypt and copy to controlled storage under an explicit retention policy. No external destination is configured automatically.

Restore into a **new, empty** database, never over the active application database: create the database with `createdb`, copy the dump into the DB container, and run `pg_restore --no-owner -U mri_user -d NEW_DATABASE DUMP_PATH`. Check row counts and Alembic version before configuring a service to use it. The verification report records the isolated restore exercise. Scheduled backups, off-site storage, RPO/RTO targets, and a monitored retention policy must be defined before production.

## Operational boundaries

- Single-worker in-memory rate limits: login 10/minute, registration 5/minute, analysis 30/minute per remote address. Configure shared storage before adding workers/replicas. Only trust forwarded addresses from explicitly configured proxies.
- Request IDs, Server-Timing, aggregate request/error/duration metrics, readiness, and container health are available. Metrics reset on process restart; no monitoring collector or alerts are provisioned.
- The development Compose stack binds ports to localhost and uses local example DB credentials. Production requires unique secrets, TLS termination, restricted network access, a resource budget, and external monitoring.
- Every analysis request requires authentication, including in development; there is no guest-analysis exception. The baseline heuristic remains the default and its empty output is `not_assessed`, never proof of a normal scan. Research FLAIR segmentation additionally requires the explicit user confirmation, configured checkpoint and database-backed report persistence.
- Analysis upload limit is 100 MiB; multipart envelope limit 101 MiB. Baseline decoded arrays are capped at 16,777,216 voxels. Research FLAIR input has a 256 MiB decoded NIfTI cap, up to 8 channels, and the same 16,777,216 spatial-voxel cap. Research requests are serialized per API process before reading/decoding to bound concurrent model memory. These bounds are engineering safeguards, not a full sandbox for untrusted medical codecs.
- JSON report export is supported. PDF generation, clinical signing, and volumetric rendering are not implemented or claimed.
