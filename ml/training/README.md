# Reproducible research training and custom datasets

This trainer learns **binary whole-tumor segmentation from axial FLAIR MRI**. It does not diagnose tumor presence, classify tumor types, assign clinical grades, or support arbitrary modalities. The app's existing heuristic workflow remains available. Experimental weights are not automatically promoted into its default analysis.

## Public source and license

The Medical Segmentation Decathlon Task01 BrainTumour is a curated glioma MRI segmentation benchmark derived from BraTS. Official metadata provides 484 labeled training cases and 266 unlabeled test cases, with FLAIR, T1w, contrast-enhanced T1, and T2 channels. This experiment uses FLAIR (channel 0), merging positive mask labels into whole tumor. Source: [AWS Open Data registry](https://registry.opendata.aws/msd/), managed by the MONAI Development Team; [dataset paper](https://arxiv.org/abs/1902.09063). License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Preserve attribution and applicable share-alike obligations when redistributing data or adaptations. No patient data is uploaded to an external service.

The downloader selects 64 patient IDs with seed 20261016 before inspecting outcomes, fetches matching image/mask files directly from the official public archive, and records SHA256 hashes. It uses only labeled cases; the official unlabeled test set cannot supply evaluation metrics. The local split is 48 training, 8 validation, 8 held-out test patients. This is a small pilot subset, not validation of the full benchmark or external clinical performance.

## Reproduce

Use Python 3.14 and the pinned backend dependencies, then install the optional training dependencies. CPU was selected for this run because the CUDA wheel download was large and unreliable; the same code accepts `--device cuda` with a compatible official PyTorch wheel.

```powershell
python -m pip install -r backend/requirements.lock
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r ml/training/requirements.txt
python -m ml.scripts.download_msd --cases 64
python -m ml.training.train_tumor --manifest ml/datasets/msd/manifest.json --output ml/runs/msd-flair-v1 --epochs 20
python -m ml.inference.predict_tumor --run ml/runs/msd-flair-v1 --image PATH_TO_FLAIR.nii.gz --output ml/runs/prediction.nii.gz
```

Download resumes via an archive index and existing files; incomplete files are replaced atomically. Increase `--cases` up to 484 for a larger independent experiment. Splits change when the case count changes, so do not compare runs as if their test cohorts were identical. Keep a fixed manifest for controlled comparisons.

Training reorients image and mask together to canonical RAS, checks their shape/affine, applies nonzero-volume z-score normalization clipped to [-5,5], resizes slices to 128x128, and samples every third axial slice. Masks use nearest-neighbor interpolation. A compact U-Net learns with BCE plus soft Dice loss. Validation Dice chooses the checkpoint; the fixed 0.5 threshold and test metrics are not used for optimization. Evaluation reports per-patient Dice, IoU, voxel sensitivity/specificity and a patient-bootstrap interval. Voxel specificity in tumor-bearing scans is **not** patient-level diagnostic specificity. Inference processes all slices and saves a canonical NIfTI mask with a matching affine and provenance sidecar.

## Your dataset and future retraining

Create a folder under ignored `ml/datasets/custom/` (or an authorized external path). Copy `custom-manifest.example.json` into it and replace the three example entries with your real cases. Relative image/label paths resolve against the manifest location. Use pseudonymous IDs, one volume per patient, and assign every patient to exactly one of `train`, `val`, `test`. Multiple visits from one patient must stay together; this initial manifest contract accepts one volume per patient. Keep related subjects/sites together when necessary and document that grouping. Do not invent missing labels.

Supported custom data: 3D FLAIR NIfTI, or 4D NIfTI with an explicit `modality_index`; aligned integer masks containing 0 background and positive labels 1..3. The trainer merges positive labels. Other modalities/tasks require a separately designed training protocol. Images/masks must be finite and share geometry. Duplicate patient IDs, repeated paths, repeated image content, mismatched supplied hashes, or missing splits fail before training.

```powershell
python -m ml.training.train_tumor --manifest ml/datasets/custom/manifest.json --output ml/runs/custom-v1 --epochs 20
```

Every run requires a new output directory and saves its resolved manifest with checksums, epoch history, selected weights, evaluation, software/device identity and checkpoint hash. Retraining starts from a fresh seeded model; it does not overwrite or silently fine-tune the previous model. Preserve an untouched external test cohort for any later promotion. The three-entry template illustrates format only and is not an adequate validation cohort.

## Security and limitations

Load only locally generated checkpoints; inference uses `torch.load(weights_only=True)` and verifies the checkpoint hash. Keep training dependencies and datasets out of the deployed inference container. The current pins (PyTorch 2.14.1 and setuptools 83.0.0) address the PYSEC-2025-194 and PYSEC-2026-3447 advisories reported for the previous pins. Re-run dependency audits when changing versions. Do not use this environment to package confidential projects.

The pilot has no independent hospital cohort, reader study, scanner/subgroup calibration, healthy control cohort, clinical outcome validation, or regulatory clearance. Small held-out samples yield uncertain estimates. A passing engineering test or high overlap score does not establish clinical safety. See the recorded evaluation rather than assuming training succeeded or accuracy is adequate.

See the [model card](../../docs/ml/MODEL_CARD.md) for the model's intended use, evaluation, deployment and limitations.

## Opt-in application inference and candidate handling

The API exposes this model only when the explicit `research_flair_segmentation` method is selected. It requires authentication and database persistence, accepts NIfTI FLAIR input only, verifies the checkpoint hash against `evaluation.json`, returns a NIfTI mask with canonical affine plus a PNG preview, and persists the report under the authenticated owner. The web and mobile clients provide a mask preview/download. It does not replace the baseline path and does not silently fall back when unavailable.

For a custom candidate, use a new immutable output directory and review the split, per-patient held-out metrics, uncertainty interval, data provenance, and checkpoint hash before configuring that run for research use. Activation is an explicit deployment configuration change to `MRI_TUMOR_MODEL_RUN_DIR` (or the host run directory in `docker-compose.research.yml`); rollback is restoring the previously recorded run path and restarting the service. Keep both run directories intact. There is no automatic candidate promotion, clinical approval, or production deployment.
