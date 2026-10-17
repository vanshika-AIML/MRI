# Backend service

FastAPI + PostgreSQL/pgvector + a heuristic MRI inference pipeline.

See the [deployment guide](../docs/DEPLOYMENT.md) and [verification report](../docs/verification/RELEASE_REPORT.md).

- Install `requirements.lock` with Python 3.14 for the validated environment.
- Set `PYTHONPATH` to both the repository root and `backend`; set `DEBUG=false`.
- Set `DATABASE_URL` and a persistent `SECRET_KEY`. Local Compose PostgreSQL uses port **55433**.
- Run `python -m alembic upgrade head` from `backend`, then `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Run `python -m pytest backend/tests ml/tests -q` from the root. Tests derive a separate database suffixed `_test` and apply real migrations. Never point `TEST_DATABASE_URL` at production.

Endpoints under `/api/v1`: health, readiness (`/ready`), metrics, registration, login, refresh, logout, profile, analysis, owned report retrieval, and versioned annotations. OpenAPI: `/docs`.

Authenticated analyses store an owned JSON report. Owners and admins can retrieve reports; radiologists can annotate their own reports, admins can annotate any report. Viewers cannot annotate. Authorization reads the current database role. Clinical study linkage is administrator-only; no result is silently attached to an arbitrary study.

Refresh rotates the account token generation. Logout and password changes revoke all sessions for the account. This account-wide policy deliberately does not provide independent device sessions.

All analysis requests require authentication in every environment. Baseline scores are unvalidated heuristic deviations, not diagnostic probabilities; an empty candidate list is reported as `not_assessed`, not as a normal scan. The optional FLAIR segmenter requires explicit user confirmation and a database-backed report; profession is self-declared and does not grant authorization. Production additionally requires a persistent secret.
