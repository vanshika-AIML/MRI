# Phase 9 System Evolution Architecture

## Overview
Phase 9 evolves the MRI Analysis System into a secure, cross-platform clinical decision support application with robust authentication, role-based authorization, controlled record modifications with immutable provenance, and unified contracts across React Web and Flutter Mobile.

```
                              ┌──────────────────────────────────┐
                              │       React Web Frontend         │
                              │ (Vite, TypeScript, TailwindCSS)  │
                              └────────────────┬─────────────────┘
                                               │
                                               │ HTTPS / JSON & Multipart
                                               ▼
┌─────────────────────────────────┐   ┌──────────────────────────────────┐
│      Flutter Mobile Client      ├──►│       FastAPI Backend API        │
│    (Android, iOS, Provider)     │   │      (Python 3.14, Async)        │
└─────────────────────────────────┘   └─┬──────────────┬───────────────┬─┘
                                        │              │               │
                                        ▼              ▼               ▼
                                 ┌────────────┐ ┌─────────────┐ ┌────────────┐
                                 │ PostgreSQL │ │ ML Pipeline │ │   Audit    │
                                 │  Database  │ │ (OpenCV, np)│ │  Logging   │
                                 └────────────┘ └─────────────┘ └────────────┘
```

---

## 1. Authentication & Permission Model

### Roles & Least-Privilege Defaults
- **Viewer (Default):** Can register, sign in, upload scans, run MRI analysis, inspect findings, and view existing clinical annotations. Cannot create or edit clinical annotations.
- **Radiologist:** Inherits Viewer capabilities. Authorized to create audited clinical annotations and observation notes. Can modify own annotations (which increments the version number and supersedes earlier records).
- **Admin:** Full administrative capabilities. Can inspect audit logs, manage user accounts, and update or supersede any annotation record.

### Security Mechanisms
- **Password Hashing:** Native `bcrypt` algorithm with per-user cryptographic salt generation.
- **Tokens:** RFC 7519 JSON Web Tokens (JWT) signed via HS256 with distinct `token_type: access` (30 min lifetime) and `token_type: refresh` (7 day lifetime).
- **Graceful DB Degradation:** The backend supports operational resilience — if the database is offline or unconfigured, analysis runs anonymously and auth endpoints respond with 503 Service Unavailable without crashing.
- **No Plaintext Leaks:** Passwords and tokens are excluded from logs, error payloads, and Pydantic response models.

---

## 2. MRI & Record Modification Safeguards

### A. Source Scan Immutability
- Uploaded MRI files (.dcm, .nii, .png, etc.) are treated as immutable raw evidence.
- Raw file bytes are hashed and preserved. Pipelines never perform destructive in-place edits on original DICOM metadata or pixel arrays.
- All enhancements (e.g. CLAHE, Gaussian denoising) produce derived artifacts with distinct stage provenance metadata.

### B. Controlled Annotation Versioning
- Radiologist annotations are stored separately from model-generated findings.
- When an annotation is updated:
  1. A new version record is generated (`version = version + 1`).
  2. The previous annotation is preserved with `superseded_by_id` pointing to the new version.
  3. An immutable audit record is logged with action `analysis.annotation_update`.
- User annotations are visibly flagged in the UI as **`CLINICAL NOTE (USER ANNOTATION — NOT MODEL FINDING)`** to prevent confusion with automated ML detections.

---

## 3. Clinical Safety & Baseline Disclosure
- The underlying signal enhancement and texture detection algorithms are heuristic baseline components (non-trained).
- Peak anomaly score represents mathematical intensity deviation thresholds and must not be interpreted as diagnostic probabilities.
- Mandatory clinical disclaimers are enforced across both Web and Mobile dashboards.
