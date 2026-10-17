# Phase 9 API Contracts & Endpoint Specifications

## Base URL
- Local Web / Dev: `http://127.0.0.1:8000`
- Android Emulator: `http://10.0.2.2:8000`
- Prefix: `/api/v1`

---

## 1. Authentication Endpoints

### `POST /api/v1/auth/register`
Creates a new user account with default `viewer` role.

**Request:**
```json
{
  "email": "radiologist@hospital.org",
  "username": "dr_smith",
  "password": "SecurePassword123!",
  "full_name": "Dr. Jane Smith, MD"
}
```

**Response (201 Created):**
```json
{
  "id": "e3a890a2-...",
  "email": "radiologist@hospital.org",
  "username": "dr_smith",
  "full_name": "Dr. Jane Smith, MD",
  "role": "viewer",
  "is_active": true,
  "is_verified": false
}
```

### `POST /api/v1/auth/login`
Authenticates user credentials and issues access & refresh JWT tokens.

**Request:**
```json
{
  "email": "radiologist@hospital.org",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 1800,
  "role": "radiologist"
}
```

### `GET /api/v1/auth/me`
Retrieves currently authenticated user profile.
- **Header:** `Authorization: Bearer <access_token>`

---

## 2. Analysis & Annotation Endpoints

### `POST /api/v1/analysis`
Executes MRI signal enhancement and baseline abnormality detection.
- **Header (Optional):** `Authorization: Bearer <access_token>` (associates analysis with user account)
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file`: Raw binary MRI file
  - `normalize`: `true` | `false`
  - `enhancement_methods`: `clahe`, `gaussian`, etc.
  - `confidence_threshold`: float between 0.0 and 1.0

### `GET /api/v1/analysis/{analysis_id}/annotations`
Lists all audited clinical annotations for a study.
- **Header:** `Authorization: Bearer <access_token>`

### `POST /api/v1/analysis/{analysis_id}/annotations`
Attaches an audited observation note to an analysis study.
- **Header:** `Authorization: Bearer <access_token>` (requires `radiologist` or `admin` role)
- **Request:**
```json
{
  "annotation_text": "Verified hyperintensity in axial slice 12; non-pathological motion artifact.",
  "field_name": "clinical_impression"
}
```
- **Response (201 Created):**
```json
{
  "id": "f51201b1-...",
  "analysis_id": "job-1234-...",
  "user_id": "e3a890a2-...",
  "annotation_text": "Verified hyperintensity in axial slice 12; non-pathological motion artifact.",
  "field_name": "clinical_impression",
  "is_original": false,
  "version": 1,
  "created_at": "2026-10-13T12:30:00Z"
}
```
