# AI-Assisted MRI Image Enhancement and Abnormality Detection System

A research application combining a FastAPI/PostgreSQL backend, deterministic MRI image-processing heuristics, an opt-in research-only trained FLAIR segmenter, a React web client, and a Flutter Android client. No model in this project is clinically validated or provides a diagnosis.

## Verification and release status

Phases 10-15 are tracked in [the verification report](docs/verification/RELEASE_REPORT.md), including actual command results, model limitations, security findings, deployment evidence, and supported targets. See [deployment and recovery](docs/DEPLOYMENT.md) and [mobile build verification](mobile/BUILD_VALIDATION.md).

Local stack: `docker compose --env-file .env.release.local --profile full-stack up -d --build` after generating a persistent `SECRET_KEY` in the ignored `.env.release.local` file. The verified local web URL is `http://127.0.0.1:5173`; API is `http://127.0.0.1:8000`. Use unique deployment credentials outside local development.

---

## Supported MRI Formats

- **DICOM**: `.dcm`, `.dicom` (Extracts patient ID, study/series UIDs, pixel array)
- **NIfTI 3D**: `.nii`, `.nii.gz` (Extracts volume dimensions & affine metadata)
- **2D Images**: `.png`, `.jpg`, `.jpeg`, `.bmp`
- **NumPy Arrays**: `.npy`, `.npz` (2D slices & 3D volumes)

---

## End-to-End Workflow

1. **Upload Scan**: Drag & drop or select supported MRI file via `frontend-web`.
2. **Choose analysis mode**: The default is the existing baseline heuristic pipeline. The opt-in `research_flair_segmentation` method requires sign-in, database persistence, a configured model run, and a FLAIR NIfTI volume (`.nii` or `.nii.gz`).
3. **Execution**: FastAPI endpoint (`POST /api/v1/analysis`) runs the selected workflow. Model errors are explicit; research segmentation does not silently fall back to heuristics.
4. **Interactive Dashboard**: Renders baseline findings or a research-model overlay preview, mask download, model provenance, and mandatory research disclaimer.
5. **Reset**: Reset action returns client UI to initial state for next scan.

---

## Mandatory Clinical Disclaimer & Research Limitations

> **RESEARCH-ONLY DISCLAIMER**: This application provides experimental image processing, heuristic indicators, or segmentation predictions for technical research only. It does not provide a clinical diagnosis, medical opinion, or confirmed lesion classification. Model masks and scores are not clinical probabilities and must not guide patient care.

---

## Local Development Quickstart

### Prerequisites
- Node.js (v18+) & npm
- Python 3.14 (validated pinned runtime)
- Git

### 1. Backend Service (FastAPI)
```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # On Windows PowerShell
# source .venv/bin/activate     # On Linux / macOS

# Install dependencies
pip install -r requirements.lock

# Start development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- Health Check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- OpenAPI Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Frontend Web (React + Vite + TypeScript)
```bash
# Navigate to frontend
cd frontend-web

# Install dependencies
npm ci

# Start Vite development server
npm run dev
```
The web client will be accessible at [http://127.0.0.1:5173](http://127.0.0.1:5173).

---

## Testing & Verification Commands

### Run Backend Tests (pytest)
```bash
pytest backend/tests
```

### Run Frontend Tests (vitest)
```bash
cd frontend-web
npm test
```

### Build Frontend Production Bundle
```bash
cd frontend-web
npm run build
```

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` in the repository root or in `frontend-web/`:
- `VITE_API_BASE_URL`: Base API URL for frontend (default: `http://127.0.0.1:8000`)
- `HOST`: Backend host interface (default: `127.0.0.1`)
- `PORT`: Backend port (default: `8000`)
- `DATABASE_URL`: PostgreSQL connection string (optional; system operates gracefully without database)

---

## Known Limitations

- **Research segmentation mode**: The API exposes a separately selected binary whole-tumor segmenter trained on axial FLAIR scans. It requires optional PyTorch runtime dependencies and a locally configured run; it is not enabled by the default deployment and has no clinical validation. See [the training guide](ml/training/README.md) and [optional deployment instructions](docs/DEPLOYMENT.md#optional-trained-model-inference).
- **Database Dependency**: PostgreSQL/pgvector database persistence is optional; system functions in degraded standalone mode if database is inactive; authentication and stored report retrieval require PostgreSQL.
