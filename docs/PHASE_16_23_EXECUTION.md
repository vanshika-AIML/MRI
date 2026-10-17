# Phases 16–23 execution tracker

Overall status: **ENGINEERING ACCEPTANCE COMPLETE; PRODUCTION/CLINICAL READINESS NOT ESTABLISHED**. No commit, push, publication, or release is authorized by the task.

Historical Phases 10–15 are not re-certified by this tracker; see [the prior verification report](verification/RELEASE_REPORT.md). All results below refer to the current workspace and must be re-run when relevant files change.

## Baseline inspection

- [x] Branch is `main`; project files are untracked in this checkout. Preserve them; do not reset, clean, or commit.
- [x] Existing pilot checkpoint exists under ignored `ml/runs/msd-flair-pilot/weights.pt`; documented SHA256: `036ac63641c4aeeb1dd8e2c0087208feaf8b42ff525b8cb16032ef33e2f48ecf`.
- [x] Existing research CLI loads the checkpoint and generated a NIfTI mask, but this code path is not called by the API.
- [x] Existing `POST /api/v1/analysis` runs only `MRIInferencePipeline` heuristics, labels it `baseline_mri_pipeline`, and persists report JSON.
- [x] Backend container copies `ml/` but does not include or mount ignored run artifacts. PyTorch is not a backend runtime dependency.
- [x] Backend, frontend, mobile, Docker Compose, API and model artifacts inspected to start the baseline.
- [x] Baseline route contract, security behavior, dependency state and platform capabilities recorded in phase evidence.

## Phase statuses

| Phase | Status | Scope and current evidence | Outstanding acceptance criteria |
|---|---|---|---|
| 16 — Trained-model integration | COMPLETE — ENGINEERING ACCEPTANCE | Explicit authenticated `research_flair_segmentation` API mode uses the actual checksum-verified checkpoint, returns a NIfTI mask/overlay/provenance, and persists a protected owner-scoped report. The baseline remains the default; model errors never fall back. Real model/API and PostgreSQL tests verify mask geometry, report retrieval, and cross-user access rejection. | No clinical validation or production approval; those are not implied by this engineering completion. |
| 17 — Evaluation and improvement | COMPLETE — EVALUATION REVIEW | Rehashed all 64 public dataset image/label pairs against the manifest; split remains 48/8/8. Re-reviewed per-patient metrics, patient bootstrap interval, sampled/resized metric semantics and limitations. No unsupported claim or unsubstantiated model improvement was made. | No further training on the held-out cohort; any improvement requires a new patient-separated experiment and untouched test cohort. |
| 18 — Custom data and retraining | COMPLETE — CONFIGURATION/FAILURE-PATH ENGINEERING ACCEPTANCE | Existing manifest and one-epoch candidate checks pass. A verified immutable candidate copy was preflighted and promoted through the read-only Compose mount, then rolled back to the original pilot. An incomplete candidate failed preflight while the active container ID and mount remained unchanged. | The candidate was a copy of the active pilot, so this validates deployment controls, not new model quality. No automated registry, clinical approval, cross-site validation, or larger custom cohort is provided. |
| 19 — Safety, privacy and security | COMPLETE — ENGINEERING REVIEW | Research mode requires a valid account UUID and DB, sanitizes stored filenames, imposes upload/decompression/voxel/channel caps, serializes model requests, protects report retrieval, verifies checkpoint hash, uses `weights_only=True`, and never silently falls back. Database-backed owner/access tests pass. Backend and training dependency audits report no known vulnerabilities. | This scoped engineering review and dependency audit are not a penetration test, clinical safety validation, or regulatory assessment. |
| 20 — Performance and deployment | COMPLETE — LOCAL INTEGRATED STACK | Full model-enabled Compose stack is running with DB, API and web services healthy; API health/readiness report DB connectivity. Authenticated synthetic FLAIR inference returned a mask and an owner-scoped report. Retrieval passed after both API and PostgreSQL container restarts. | Local engineering deployment only. No production TLS/proxy, cold-start/concurrency capacity study, external monitoring, or production resource limits are verified. |
| 21 — Frontend and cross-platform acceptance | COMPLETE — AVAILABLE TARGETS | Chrome completed registration, login, research-mode selection, synthetic NIfTI upload, inference, results preview and mask-download display against Compose. Android emulator (Android 17/API 37) passed baseline and authenticated research segmentation/report-retrieval integration tests. | iOS is unsupported/unverified in this checkout; no physical Android device was available or tested. |
| 22 — Final regression/release candidate | COMPLETE — INTEGRATED ENGINEERING GATES | Python, web and Flutter regressions pass. The integrated Compose API was exercised with authenticated inference/report persistence and API/database restart recovery; Chrome and Android emulator completed the workflow. Nginx response headers, 404 behavior, app assets and crawler policy were verified. | Not a production or clinical release candidate: no external security penetration test, clinical validation, iOS workflow, TLS deployment, or production capacity/monitoring gates. |
| 23 — Documentation and handover | COMPLETE — ENGINEERING HANDOVER | Deployment guide, phase tracker, model card and release report now reflect local integrated deployment, promotion/rollback failure handling, Android/Chrome evidence, web launch audit, and remaining gates. | No commit, release, publication, or clinical approval is authorized. |

## Phase evidence and change log

New commands, exit codes, failures, fixes, artifact paths, and phase-boundary statuses are appended here as work proceeds. Do not mark a phase PASS until all critical acceptance criteria are verified.

### Phase 16–23 work log

- `python -m pytest ml/tests/test_tumor_segmenter.py ml/tests/test_training_contract.py backend/tests/test_analysis_api.py -q`: **23 passed**. Includes actual checkpoint API integration, output mask geometry/labels, 3D/4D inputs, no-fallback behavior, auth/database requirements, and one-epoch custom candidate training.
- `python -m pytest backend/tests ml/tests -q` with `TEST_DATABASE_URL` pointing to isolated `mri_phase16_23_test`: **195 passed, zero skipped**, 4 pre-existing deprecation warnings. The authenticated workflow test stored and retrieved the actual-model report and rejected another account.
- Dataset revalidation via `validate_manifest(ml/datasets/msd/manifest.json)`: **64 cases**, split `48 train / 8 val / 8 test`, all image and label hashes matched.
- Full-volume service inference, held-out `BRATS_096`: **2.605 s** on local CPU; `240×240×155`; 87,513 predicted voxels; input/checkpoint/mask hashes and output affine recorded in [Phase 16 inference evidence](verification/phase16-model-api-inference.json). This is a one-volume engineering timing, not a capacity claim.
- `npm test`: **6 passed**; `npm run lint`: passed; `npm run build`: passed.
- `flutter analyze`: **No issues found**; `flutter test`: **9 passed**.
- `pip-audit -r backend/requirements.lock` and `pip-audit -r ml/training/requirements.txt`: **No known vulnerabilities found**; `pip check`: no broken requirements.
- `docker compose -f docker-compose.yml -f docker-compose.research.yml --profile full-stack up -d --build`: passed. All three services (`db`, `backend`, `frontend-web`) reported healthy with the pilot checkpoint mounted read-only.
- `GET /api/v1/health` reported overall `ok` and database `ok`; `/api/v1/ready` returned `ready: true`.
- Authenticated live API inference on synthetic `24×20×5` FLAIR NIfTI returned 169 predicted voxels. The owner retrieved the persisted report after backend restart and again after PostgreSQL container restart; readiness recovered in both cases.
- Phase 18 deployment-control exercise: incomplete checkpoint run rejected by preflight without changing active container ID or model mount; verified immutable candidate copy was promoted; rollback restored `ml/runs/msd-flair-pilot`; API readiness recovered after both switches. Candidate copy was deleted after the test.
- `flutter test integration_test/system_workflow_test.dart -d emulator-5554`: **2 passed** on Android emulator, Android 17/API 37; covered authenticated baseline and research segmentation, including report retrieval.
- Chrome against the running Compose web service completed registration, login, research mode selection, synthetic NIfTI upload, inference, results preview and mask-download display.
- `nginx -t`: passed. Static responses include CSP, Permissions-Policy, X-Content-Type-Options, Referrer-Policy and X-Frame-Options; an unknown URL returned the custom 404 with HTTP 404. Manifest, icon and `robots.txt` returned HTTP 200.
- `docker compose build backend`: passed for the default baseline-only image; `docker run --rm --entrypoint python mri-backend:latest -c "import app.main, sys; print('torch_loaded=' + str('torch' in sys.modules))"` reported `torch_loaded=False`.
- Backend import smoke check reports `torch_loaded=False` with the default settings, confirming PyTorch remains optional for baseline startup.
- Initial full-volume test exposed that the baseline 128 MiB decoded-size limit rejected the legitimate four-channel MSD NIfTI; research-mode decoding was capped separately at 256 MiB and the held-out volume then passed. No input or model artifact was modified.

### Post-rework verification — 2026-10-16

- The updated model-enabled Compose backend and web image were rebuilt. The existing PostgreSQL volume was retained; backend startup applied Alembic revision `005_self_declared_profession`. All three services reported healthy, `/api/v1/ready` and the web root returned HTTP 200, and the `users.profession` column is present.
- Focused backend checks in the existing dependency image: analysis API **17 passed**; auth/role/registration checks **20 passed, 10 deselected**; checkpoint inference/training-contract checks **7 passed**.
- The connected workflow test passed (**1 passed**) on a fresh uniquely named test database and the test database was dropped afterwards. The first invocation against the pre-existing `mri_db_test` failed setup because that database already had a `patients` table; it was left untouched.
- Web regressions: **8 passed**; lint and production build passed. Flutter unit/widget tests: **11 passed** and `flutter analyze` reported no issues.
- Android emulator (Android 17/API 37): **2 integration tests passed** against a temporary model-enabled API and disposable database, covering authenticated baseline and research segmentation/report retrieval. The temporary service and database were removed.
- Browser workflow against an isolated API/database completed registration, login, self-declared `researcher` profession while preserving `viewer` authorization, explicit FLAIR confirmation, research inference, report persistence, JSON download toast and logout to the sign-in gate. The synthetic volume returned zero predicted voxels and `not_assessed`; this is integration evidence only, not model-quality evidence. Temporary test data and service were removed.
- The legacy empty-baseline web result now suppresses historical “no abnormalities flagged” summaries and displays `not_assessed`. Web tests verify the JSON export uses the canonical response JSON, `application/json`, the `mri-<analysis_id>.json` filename, and a success toast.
- No model threshold/weight was changed, no new candidate was trained, no new packages were installed, and no commits/releases were created. The broader visual redesign, clinical validation, production TLS/secrets/monitoring and unsupported device testing remain open.

No files were committed, pushed, published, or released. All repository files remain untracked in this checkout; preserve them.
