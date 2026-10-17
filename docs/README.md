# Project Documentation

Welcome to the documentation repository for the AI-Assisted MRI Image Enhancement and Abnormality Detection System.

## Documentation Structure

- `architecture/`: System design, monorepo architecture, component interaction diagrams, security and compliance guides (e.g., HIPAA / DICOM handling).
- `api/`: REST API specifications, OpenAPI contracts, request/response schemas, and integration guides for web and mobile clients.
- `ml/`: Model architecture papers, benchmark datasets, evaluation protocols, training procedures, and clinical validation metrics.
- [Model card](./ml/MODEL_CARD.md): intended use, evaluation, limitations and current deployment status of the experimental FLAIR segmenter.
- [Launch audit](./verification/LAUNCH_AUDIT.md): itemized applicability review of the web launch checklist.
- [Release verification](./verification/RELEASE_REPORT.md): engineering evidence and remaining nonclinical release gates.
- [Deployment and recovery](./DEPLOYMENT.md): local Compose, model selection, candidate rollback and operational limits.
