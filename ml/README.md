# Machine Learning Workspace (MRI Models)

This workspace contains deterministic image enhancement, heuristic anomaly detection, and an optional research-only FLAIR tumor-segmentation trainer. No trained checkpoints or clinical validation cohorts are shipped in this repository; dataset and run artifacts are gitignored.

Run `python -m ml.evaluation.validate_baseline --output docs/verification/model-baseline.json` from the root for the seeded synthetic engineering baseline. See `docs/verification/RELEASE_REPORT.md` for results and limitations.

## Structure Overview

- `datasets/`: Dataset storage, data manifest definitions, and split configurations (raw and processed MRI datasets are excluded from version control).
- `preprocessing/`: MRI-specific preprocessing pipelines (DICOM/NIfTI parsing, intensity normalization, skull stripping, bias field correction, slice extraction, data augmentation).
- `training/`: Reproducible patient-separated FLAIR segmentation training and evaluation, plus a custom-manifest path for authorized local datasets. See [`training/README.md`](training/README.md).
- `evaluation/`: Model evaluation metrics (Dice score, IoU, Sensitivity, Specificity, ROC-AUC, SSIM, PSNR) and validation reporting.
- `inference/`: Existing heuristic pipeline and the separately selected, optional FLAIR research segmenter used by the backend API. The trained model is lazy-loaded, checksum-verified and never used as an automatic fallback.
- `models/`: Neural network architecture definitions (e.g., U-Net, Swin UNETR, Vision Transformers, custom CNNs) and local weights checkpoints (checkpoint weights are gitignored).
- `notebooks/`: Exploratory data analysis (EDA), prototype experiments, and visualization notebooks.
- `scripts/`: CLI helper scripts for batch preprocessing, model export, and benchmark execution.
- `tests/`: Unit and integration tests for data loaders, preprocessing transforms, and model architectures.

- `enhancement/`: Image enhancement modules (CLAHE, histogram equalization, Gaussian/NLM denoising, unsharp mask sharpening) with base interface and structured results.
- `detection/`: Abnormality detection modules (intensity anomaly, texture anomaly) with model-agnostic region output, confidence scores, and severity levels.

## Phase Status
- **Phase 1 Complete**: Monorepo directory structure established.
- **Phase 4 Complete**: DICOM reader (`pydicom`), NIfTI reader (`nibabel`), intensity normalization (Z-score, Min-Max, windowing), resampling, Otsu masking, N4 bias correction, synthetic MRI generator (`ml/scripts/generate_synthetic_data.py`), and backend `IngestionService` fully implemented and tested (17 ML unit tests passing).
- **Phase 5 Complete**: AI Enhancement + Abnormality Detection foundation — CLAHE/histogram equalization/denoising/sharpening enhancers, intensity/texture anomaly detectors, `ModelRegistry` for pluggable models, end-to-end `MRIInferencePipeline` (preprocessing → enhancement → detection → result), typed Pydantic I/O schemas, and 97 ML unit tests passing.
