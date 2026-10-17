# MRI AI Enhancement & Abnormality Detection — Web Portal (Phase 7)

Modern responsive web application built with React 19, TypeScript, Vite, and Tailwind CSS. Connects to the FastAPI backend API (`POST /api/v1/analysis`) to provide an end-to-end MRI scan ingestion, intensity normalization, contrast enhancement, and heuristic abnormality detection workflow.

---

## Features & Analysis Workflow

1. **Scan Selection & Validation**:
   - Drag-and-drop or file browser upload.
   - Client-side format validation: DICOM (`.dcm`), NIfTI 3D (`.nii`, `.nii.gz`), Image (`.png`, `.jpg`, `.jpeg`, `.bmp`), and NumPy (`.npy`, `.npz`).
   - File size validation (100MB max limit, 0-byte detection).
2. **Pipeline Customization Options**:
   - Normalization mode toggle (Min-Max scaling vs Z-score).
   - Image Enhancement method selection (CLAHE, Gaussian smoothing, Histogram Equalization, Unsharp Masking).
   - Abnormality Detection threshold slider (`0.1` to `0.9`).
3. **State Management**:
   - Loading progression stepper and processing timer.
   - Comprehensive error alert banners with friendly error reporting.
4. **Structured Results Dashboard**:
   - Executive Summary (Job ID, Status, Processing Duration, Overall Severity, Peak Anomaly Score).
   - Scan Input Metadata (Format, Array Shape, Dimensions, Modality, Patient ID).
   - Interactive Stage Execution Metrics.
   - Visual Scan Viewer with bounding box region overlays `[y_min, x_min, y_max, x_max]`.
   - Detected Regions Table & Anomaly Coordinates.
   - Model & Heuristic Engine Metadata (`baseline_mri_pipeline` v1.0.0).
   - Prominent Mandatory Clinical Disclaimer.
5. **Reset Workflow**:
   - "Analyze Another Scan" button resets state cleanly without requiring a browser refresh.

---

## Local Development & Environment Setup

### 1. Environment Configuration
Create or edit `.env` in `frontend-web/`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```
*(If the backend runs on port 8001, the client automatically attempts port fallback).*

### 2. Install Dependencies
```bash
cd frontend-web
npm install
```

### 3. Start Vite Development Server
```bash
npm run dev
```
Access client interface at `http://127.0.0.1:5173`.

### 4. Build Production Bundle
```bash
npm run build
```

### 5. Run Automated Tests
```bash
npm test
```

---

## Clinical Safety & Baseline Limitations

- **Non-Diagnostic Tool**: This application is a research and technical evaluation platform. It does **NOT** provide medical diagnoses, clinical grading, or confirmed lesion classifications.
- **Baseline Heuristic Model**: The active detection engine (`is_baseline: true`) calculates mathematical signal intensity/texture variance thresholds.
- **No Disease Diagnosis**: When zero candidate regions are flagged, the interface displays: *"No candidate abnormalities were returned by the current baseline detector."*
