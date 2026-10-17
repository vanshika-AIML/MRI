# Release verification report

**Verification date:** 2026-10-16  
**Status:** Engineering/research release candidate only. Not for clinical use.

Phases 10-15 are the historical baseline. The later Phase 16-23 continuation adds an integrated local model-enabled Compose deployment, authenticated web and Android workflows, candidate-path failure/promotion/rollback checks, and updated launch documentation. Passing engineering tests or overlap metrics does not establish diagnostic accuracy, safety, regulatory compliance, or production readiness.

## Phase results

| Phase | Result | Evidence |
|---|---|---|
| 10 — End-to-end integration | Registration, login, inference, report persistence, annotation, and cross-user report access rejection passed. Backend tests passed against a fresh isolated PostgreSQL test database. | `backend/tests/test_system_workflow.py`; 87 backend tests passed |
| 11 — Model and MRI pipeline | The heuristic pipeline baseline is recorded. A separate FLAIR whole-tumor segmentation pilot trained on 64 MSD patients and was evaluated once on 8 held-out patients. Checkpoint inference produced a binary NIfTI mask with matching canonical geometry and verified hashes. | [Pilot evaluation](./msd-flair-pilot-evaluation.json); [inference provenance](./msd-flair-pilot-inference.json); [training guide](../../ml/training/README.md) |
| 12 — Security and reliability | Backend and web dependency audits have no known vulnerabilities in their audited dependency sets. Optional training pins were upgraded after the audit identified vulnerable earlier pins; the final training dependency audit is clean. Access-control and token-revocation regression tests passed. | [Backend audit](./python-audit-final.json); [web audit](./npm-audit-final.json); [training audit](./python-training-audit-final.json) |
| 13 — Mobile acceptance | Android registration, login, synthetic scan upload/analysis, report retrieval, and logout passed against the local API and database. Android build and Flutter checks passed. iOS is not supported or verified in this checkout. | [Mobile verification](../../mobile/BUILD_VALIDATION.md); `android-e2e-final.log` |
| 14 — Performance and deployment | The local API, PostgreSQL, and web containers were healthy. A synthetic 16-request run at concurrency 4 measured HTTP p50 34.2 ms and p95 54.4 ms; malformed-upload recovery and backup/restore into a separate database passed. | [Container health](./container-health.json); [performance](./performance-container.json); `container-build-final.log` |
| 15 — Regression and release gate | Backend and ML suites passed (87 + 100 tests). Web tests, lint, and production build passed. Flutter dependency resolution, format, analysis, tests, and Android debug APK build passed. | [Phase 15 command results](./phase15-training-final/results.json) |

## Current integrated verification (Phases 16-23)

**Verification date:** 2026-10-16  
**Result:** Local engineering acceptance passed; no production or clinical release is authorized.

- The complete model-enabled Compose profile was built and started. `db`, `backend`, and `frontend-web` reported healthy; API health and readiness confirmed PostgreSQL connectivity.
- An authenticated synthetic `24×20×5` FLAIR NIfTI request returned a research mask with 169 predicted voxels. The owner retrieved the saved report after API restart and after PostgreSQL container restart; readiness recovered.
- Candidate handling was exercised with an immutable copy of the active pilot: preflight passed, the copy was mounted/promoted, and rollback restored the original pilot. An incomplete candidate was rejected before activation and left the active container and model mount unchanged. This verifies configuration safety, not candidate quality.
- Chrome completed authenticated research-mode upload, inference, preview, JSON export toast, and mask-download display. Android emulator (Android 17/API 37) passed two integration tests covering baseline and authenticated research-mode inference/report retrieval. iOS and physical Android were not tested.
- Current regression: **195 Python tests passed** with 4 dependency deprecation warnings; **6 web tests passed**; web lint/build passed; Flutter analysis passed with no issues and **9 Flutter tests passed**; **2 Android emulator integration tests passed**.
- The local static host passes `nginx -t`; it returns a branded HTTP 404 and sends CSP, Permissions-Policy, X-Content-Type-Options, Referrer-Policy and X-Frame-Options. The site is intentionally `noindex` and disallows crawlers. HSTS belongs at the production TLS terminator.
- The local smoke deployment used a generated test-only `SECRET_KEY` set in the running container environment. It is not committed or retained in deployment configuration; a future Compose recreation without a configured persistent secret will invalidate tokens. Configure a durable secret before shared or production use.

See the [integrated deployment evidence](./phase18-22-integrated-deployment.json), [web launch audit](./LAUNCH_AUDIT.md), [model card](../ml/MODEL_CARD.md), and [deployment guide](../DEPLOYMENT.md). Remaining gates include TLS, restricted production networking, external monitoring/alerting, backup retention and RPO/RTO, production capacity/concurrency testing, independent clinical validation and regulatory review. The model remains experimental and must not guide patient care.

### Post-rework verification (2026-10-16)

- Rebuilt the model-enabled Compose backend and web images; startup applied Alembic revision `005_self_declared_profession` to the existing database without recreating its volume. Backend, database and web returned healthy; API readiness and frontend HTTP checks returned 200. The profession column is present.
- Backend regressions in the existing locked-dependency image: analysis API **17 passed**; focused auth/access checks **20 passed, 10 deselected**; actual-checkpoint inference/training contracts **7 passed**. The connected authentication, profession, baseline/research inference, report persistence, refresh/logout, annotations and cross-user owner-isolation workflow passed (**1 passed**) on a uniquely named disposable PostgreSQL database, which was removed after the run.
- Web: **8 tests passed**; container production build passed. Flutter unit/widget tests: **11 passed**. Android 17/API 37 emulator integration tests: **2 passed** against a temporary model-enabled API and disposable database; both baseline and research workflows retrieved their reports. The temporary API/database were removed. No package was installed.
- Browser E2E against an isolated API/database completed registration, login, self-declared `researcher` profession with `viewer` permissions, explicit FLAIR confirmation, research inference, persisted report, JSON download toast and logout to the sign-in gate. The synthetic volume returned 0 predicted voxels and `not_assessed`; it is workflow evidence only. The signed-out screen also hides upload controls. No test account/report was left in the retained application database.
- The synthetic empty-baseline regression now requires `not_assessed` when there are no regions. No model weights or thresholds were changed, no candidate was trained, and no diagnostic-performance improvement is claimed.

## Segmentation pilot

- **Source:** Medical Segmentation Decathlon Task01 BrainTumour, downloaded from the official public AWS mirror; CC BY-SA 4.0. The subset was selected deterministically with seed `20261016`; no MRI data was uploaded to an external service.
- **Task:** Binary whole-tumor mask (`label > 0`) from axial FLAIR, channel 0. Patient-level split: 48 train / 8 validation / 8 test out of 64 selected labeled cases.
- **Training:** Compact 2D U-Net; 10 epochs; 96x96 slices; every sixth axial slice; CPU; PyTorch 2.14.1; seed `20261016`. Validation Dice selected the checkpoint; the test split was not used for optimization.
- **Held-out result:** Mean patient Dice `0.7735`, bootstrap 95% interval `[0.6630, 0.8614]` across only 8 test patients; best validation Dice `0.7315`. Metrics are at resized/sampled slice resolution.
- **Inference check:** Held-out `BRATS_096` produced a binary mask of shape `240x240x155`, with canonical affine retained and both input/checkpoint/output hashes verified.
- **Checkpoint:** `ml/runs/msd-flair-pilot/weights.pt`, SHA256 `036ac63641c4aeeb1dd8e2c0087208feaf8b42ff525b8cb16032ef33e2f48ecf`. Dataset and model weights are excluded from version control; the training command regenerates them.

This small public-data experiment is not independent clinical validation. It has no external-site cohort, reader study, scanner/subgroup calibration, healthy-control cohort, clinical outcomes, subtype/grade prediction, or regulatory clearance. At the time of this historical Phase 10–15 report, the model was not connected to the application's heuristic analysis endpoint. The subsequent API integration and its incomplete release gates are tracked separately in [the Phase 16–23 execution tracker](../PHASE_16_23_EXECUTION.md).

## Regression and operational notes

- Fresh final run: `87 passed` in `backend/tests` with PostgreSQL enabled; `100 passed` in `ml/tests` using the optional PyTorch environment. Four existing deprecation warnings remain in the backend suite (`httpx` with Starlette `TestClient`, and `asyncio.iscoroutinefunction` in SlowAPI).
- The final web dependency audit covered 177 packages and reported zero vulnerabilities. The final backend dependency audit and the optional training requirements audit also reported no known vulnerabilities. Re-audit dependencies when pins change.
- The 16-request performance run used synthetic input on this development host. Python `tracemalloc` peaked at about 11.8 MB and excludes native allocations; these measurements are not a production capacity target.
- The local Compose stack is bound to loopback and uses development configuration. Production still needs unique secrets, TLS, restricted networks, external monitoring/alerting, defined backup retention and RPO/RTO, and a qualified medical-device safety/regulatory process.

## Reproduction and limitations

Follow the [training guide](../../ml/training/README.md) to download the seeded subset, train a new run, evaluate it, or provide an authorized local dataset through a custom manifest. Keep source attribution and comply with the dataset license when redistributing data or adaptations. Model outputs remain experimental and must not be used to make clinical decisions.

See [deployment and recovery](../DEPLOYMENT.md) for local operation and the remaining production gates.
See the [model card](../ml/MODEL_CARD.md) for intended use, limitations, evaluation and governance.
