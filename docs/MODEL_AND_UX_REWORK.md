# Model and UX Rework Execution Record

**Overall status:** IN PROGRESS. Empty heuristic outputs now report `not_assessed`, and the stale API test expectation has been corrected. The trained model remains a small research-only FLAIR segmentation model; this work does not establish diagnostic performance or clinical readiness.

## Priority status

| Priority | Status | Root cause / reason | Remaining acceptance work |
|---|---|---|---|
| 1 — Model failure and safe interpretation | PARTIAL | Uploads default to `baseline_mri_pipeline`; an empty heuristic region list was converted to `severity="normal"` and the detector summary said “No abnormalities detected.” The trained FLAIR segmenter is opt-in and performs segmentation, not universal abnormality detection. | Empty outputs now remain inconclusive end-to-end. No validated general abnormality classifier or negative-control evaluation cohort exists; do not train/promote a candidate without a justified experiment and untouched evaluation set. |
| 2 — Authentication and profession access | COMPLETE — ENGINEERING | Profession is persisted separately from authorization; users remain `viewer` by default. Auth-first web/mobile gates, password visibility, refresh/logout and owner/role behavior are covered by focused and integrated tests. | Profession remains self-declared, not credential verification; real production identity/session policy is outside this local acceptance. |
| 3 — Visual redesign and copy | PARTIAL | Auth-first sign-in, accessible profession/password controls, a unified dark web research-workbench shell, and research-first web/mobile copy are implemented. Deeper screen-specific layout changes remain outstanding. | Continue accessible visual/interaction review without adding dependencies or overstating clinical capability. |
| 4 — Report export | PARTIAL — JSON ONLY | Existing JSON report download now has exact payload, MIME, filename, link and toast assertions; research mask NIfTI download is visible and the report remains owner-scoped. | No separate JSON result tab or PDF/HTML generator exists; those formats are not claimed. |
| 5 — Integrated end-to-end workflow | COMPLETE — ENGINEERING | Updated Compose stack is healthy with migration 005 applied; browser completed registration, login, confirmed FLAIR upload, inference, JSON-download toast and logout using an isolated DB. Android emulator baseline/research/report workflows passed against a separate disposable API/DB. | No clinical or production readiness is implied. |

## Priority 1 — Root-cause observations

- Synthetic uniform 3D NumPy upload reproduced a successful baseline response with `model_name=baseline_mri_pipeline`, zero candidate regions, `severity=normal`, and summary `Detection: no abnormalities flagged.` This is an interpretation defect, not evidence that every model prediction is empty.
- After the correction, an empty baseline result has `severity=not_assessed`, an explicit warning, and no claim that the image is normal. The legacy `normal` severity is likewise rendered as “not assessed” in the web/mobile clients.
- The API's synthetic bright-spot PNG is a software contract fixture, not clinical ground truth; it is not evidence that the baseline can recognize lesions. This change deliberately does not tune heuristic thresholds or claim detection performance.
- The upload form defaults to the baseline heuristic. `research_flair_segmentation` must be explicitly selected and requires an authenticated user, DB persistence, NIfTI input, and a configured local checkpoint.
- The trained model is a compact 2D U-Net for binary whole-tumor (`label > 0`) segmentation from a user-supplied FLAIR volume; it is not a general MRI classifier. Checkpoint loading uses `weights_only=True` and verifies the SHA-256 in run metadata.
- Training and inference share canonical orientation and nonzero-volume z-score normalization clipped to [-5, 5]; inference processes all axial slices and restores a mask to source geometry. Sequence identity cannot be independently established from arbitrary NIfTI voxel data and must not be represented as verified metadata.
- Existing held-out pilot evidence: 8 positive test patients, mean patient Dice 0.7735, bootstrap 95% interval [0.6630, 0.8614], and per-patient voxel-level sensitivity/specificity in [the model evaluation](verification/msd-flair-pilot-evaluation.json). No negative/healthy test patients are available; patient-level diagnostic specificity, true clinical false-positive rate, and clinical sensitivity are not established. The evaluator's test metrics are at sampled/resized slice resolution.
- The previous promotion exercise used a byte-identical copy of the active checkpoint. It validates activation/rollback controls, not candidate performance improvement.

## Change log

| Change | Files |
|---|---|
| Reproduced empty baseline outputs and replaced “normal/no abnormalities” interpretation with “not assessed”; response warning now says an empty heuristic result cannot establish normality. | `backend/app/services/analysis.py`, `backend/app/schemas/analysis.py`, `ml/detection/base.py`, `ml/inference/pipeline.py` |
| Updated web/mobile severity presentation so legacy `normal` heuristic labels are displayed as “not assessed,” not as a reassuring result. | `frontend-web/src/components/ResultsDashboard.tsx`, `mobile/lib/models/analysis.dart`, `mobile/lib/widgets/severity_badge.dart` |
| Added authentication-required analysis access, explicit self-declared FLAIR confirmation for research segmentation, separate self-declared profession metadata, additive migration, authentication-first web/mobile gates, and accessible password visibility controls. Profession selection does not grant authorization. | `backend/app/api/routes/analysis.py`, `backend/app/models/user.py`, `backend/app/schemas/auth.py`, `backend/app/services/auth.py`, `backend/app/api/routes/auth.py`, `backend/alembic/versions/005_self_declared_profession.py`, `frontend-web/src`, `mobile/lib` |
| Updated old baseline reports at render time so legacy `normal` status and reassuring “no abnormalities flagged” summaries display as inconclusive; clarified heuristic-only signal labels and removed sign-in copy from an already authenticated workspace. | `frontend-web/src/components/ResultsDashboard.tsx`, `frontend-web/src/App.tsx`, `frontend-web/src/components/Header.tsx`, `frontend-web/src/components/FileUpload.tsx` |
| Unified the authenticated web workspace on its existing dark/cyan research palette and aligned mobile workspace/method labels with the nonclinical research contract; shortened the mobile dropdown label after narrow-layout tests caught a flex overflow. | `frontend-web/src/App.tsx`, `frontend-web/src/components/Header.tsx`, `mobile/lib/screens/upload_screen.dart`, `mobile/test/widget_test.dart` |
| Added regression coverage requiring `not_assessed` for empty API results, safe legacy web rendering, and exact JSON download payload/MIME/filename behavior. | `backend/tests/test_analysis_api.py`, `frontend-web/src/App.test.tsx` |

## Commands and results

- Synthetic reproducer before fix: `AnalysisService` returned `success=True`, baseline model, zero regions, `severity=normal`, and “no abnormalities flagged.”
- Same synthetic service path after fix: `severity=not_assessed` with a warning that no candidates do not establish normality.
- Web: 8 tests passed; lint and production build passed after the auth-first and interpretation changes.
- Mobile: `flutter analyze` passed; 11 unit/widget tests passed; formatting is clean.
- Backend, run inside the existing `mri-backend` image with the workspace mounted (no dependency installation): `backend/tests/test_analysis_api.py` — 17 passed; focused auth validation/access tests — 20 passed, 10 deselected.
- Real-checkpoint inference and training-contract tests, same existing image: 7 passed.
- Connected auth/profession, baseline and research inference, report persistence, annotations, refresh/logout and cross-user access workflow: 1 passed on a uniquely named disposable PostgreSQL database; that database was removed. An initial run against the pre-existing shared `mri_db_test` stopped at its already-present `patients` table; it was not deleted or altered.
- Web: 8 tests passed, including a legacy-empty-result check and exact JSON report payload, MIME, filename and download-toast assertions; lint and production build passed.
- Flutter: 11 unit/widget tests passed; `flutter analyze` reported no issues. Android 17/API 37 emulator: 2 integration tests passed against an isolated API and disposable DB, covering baseline and confirmed FLAIR inference/report retrieval; the test service and DB were removed.
- Browser E2E against an isolated API/DB: registration as a self-declared researcher retained `viewer` permissions; authenticated synthetic FLAIR upload returned a research mask with 0 predicted voxels and `not_assessed`; DB report persisted; JSON download toast appeared; logout returned to sign-in with upload controls hidden. The synthetic result is software workflow evidence, not model-quality evidence.
- Rebuilt model-enabled local Compose backend and web image. All services are healthy; Alembic is at `005_self_declared_profession` and the existing DB contains the new profession column. The normal application DB volume was not recreated and no test accounts/reports were left in it.
- Local system Python remains missing existing dependencies, so focused Python tests were run in the project image. No package was installed.
- Production/clinical gates remain: the broader visual redesign, independent sequence validation, healthy/negative evaluation cohort, clinical review, production TLS/secrets/monitoring and iOS/physical-device acceptance.

## Dataset, training, and model artifact record

- Existing data: Medical Segmentation Decathlon Task01 BrainTumour; public AWS Open Data mirror, CC BY-SA 4.0; 64 labeled cases recorded in the manifest with patient-level 48/8/8 train/validation/test splits and per-file SHA-256 hashes. No data was acquired or downloaded for this rework.
- Existing checkpoint: `ml/runs/msd-flair-pilot/weights.pt`; SHA-256 `036ac63641c4aeeb1dd8e2c0087208feaf8b42ff525b8cb16032ef33e2f48ecf`; compact 2D U-Net, FLAIR channel 0, size 96, slice stride 6, threshold 0.5, 10 epochs, seed 20261016, PyTorch 2.14.1 CPU.
- No new candidate was trained in this rework yet. The corrected behavior is reporting semantics; it does not imply improved model weights. A separate candidate requires a reproducible experiment and a justified acceptance criterion, without overwriting the active run.

## Remaining risks and blockers

- Self-reported profession must remain distinct from authorization and is not credential verification.
- NIfTI input does not reliably encode sequence/anatomy; research segmentation depends on honest FLAIR selection and currently has no independent sequence classifier.
- The dataset has no negative/healthy control cohort, only eight held-out tumor-positive patients, no external site/reader study, and no clinical calibration or validation.
- The test runner in the current local Python environment lacks `slowapi`; adding/installing packages is out of scope without approval.
- Production TLS, durable secrets, monitoring, capacity testing, clinical validation, and regulatory review remain outside this local engineering acceptance.
