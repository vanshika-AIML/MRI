import type { AnalysisOptions, AnalysisResponse, ApiError } from '../types/analysis';

/**
 * Configure API Base URL from environment variables, fallback to default ports.
 */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000'
    : 'http://127.0.0.1:8000');

/**
 * Executes MRI AI Inference analysis request against POST /api/v1/analysis.
 *
 * @param file Uploaded MRI File object (.dcm, .nii, .nii.gz, .png, .jpeg, .npy, .npz)
 * @param options Optional pipeline configuration parameters
 * @returns Structured AnalysisResponse object
 */
export async function runMriAnalysis(
  file: File,
  options?: AnalysisOptions
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (options?.analysis_method) {
    formData.append('analysis_method', options.analysis_method);
  }
  if (options?.flair_sequence_confirmed !== undefined) {
    formData.append('flair_sequence_confirmed', String(options.flair_sequence_confirmed));
  }

  if (options?.normalize !== undefined) {
    formData.append('normalize', String(options.normalize));
  }
  if (options?.normalization_method) {
    formData.append('normalization_method', options.normalization_method);
  }
  if (options?.enable_enhancement !== undefined) {
    formData.append('enable_enhancement', String(options.enable_enhancement));
  }
  if (options?.enhancement_methods && options.enhancement_methods.length > 0) {
    formData.append('enhancement_methods', options.enhancement_methods.join(','));
  }
  if (options?.enable_detection !== undefined) {
    formData.append('enable_detection', String(options.enable_detection));
  }
  if (options?.detection_methods && options.detection_methods.length > 0) {
    formData.append('detection_methods', options.detection_methods.join(','));
  }
  if (options?.confidence_threshold !== undefined) {
    formData.append('confidence_threshold', String(options.confidence_threshold));
  }
  if (options?.study_id) {
    formData.append('study_id', options.study_id);
  }

  let response: Response;
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('mri_access_token') : null;
  const requestHeaders: Record<string, string> = {};
  if (token) {
    requestHeaders['Authorization'] = `Bearer ${token}`;
  }

  try {
    response = await fetch(`${API_BASE_URL}/api/v1/analysis`, {
      method: 'POST',
      headers: requestHeaders,
      body: formData,
      signal: AbortSignal.timeout(120000),
    });
  } catch {
    throw new Error('Unable to connect to the configured backend API. Check the server address and network connection.');
  }

  if (!response.ok) {
    let errorMsg = `Server error (${response.status})`;
    try {
      const errJson = (await response.json()) as ApiError & { detail?: unknown };
      if (errJson?.error?.message) {
        errorMsg = errJson.error.message;
      } else if (errJson?.detail) {
        errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      if (response.status === 413) {
        errorMsg = 'Uploaded file exceeds the maximum allowed size limit of 100MB.';
      } else if (response.status === 400) {
        errorMsg = 'Invalid, corrupt, or unsupported MRI scan file.';
      }
    }
    throw new Error(errorMsg);
  }

  const data = (await response.json()) as AnalysisResponse;
  return data;
}

/**
 * Health check helper for backend availability probe.
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/health`, { method: 'GET', signal: AbortSignal.timeout(10000) });
    return res.ok;
  } catch {
    return false;
  }
}

export interface AnnotationItem {
  id: string;
  analysis_id: string;
  user_id: string;
  annotation_text: string;
  field_name?: string | null;
  is_original: boolean;
  version: number;
  created_at: string;
}

/**
 * Fetch clinical annotations for an analysis run.
 */
export async function getAnalysisAnnotations(analysisId: string): Promise<AnnotationItem[]> {
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('mri_access_token') : null;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/v1/analysis/${analysisId}/annotations`, {
    method: 'GET',
    headers,
  });

  if (!res.ok) {
    if (res.status === 503) return [];
    if (res.status === 401) return [];
    throw new Error(`Failed to load annotations (${res.status})`);
  }

  return (await res.json()) as AnnotationItem[];
}

/**
 * Post a new clinical annotation to an analysis run.
 */
export async function createAnalysisAnnotation(
  analysisId: string,
  annotationText: string,
  fieldName?: string
): Promise<AnnotationItem> {
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('mri_access_token') : null;
  if (!token) {
    throw new Error('Authentication required to save clinical annotations.');
  }

  const res = await fetch(`${API_BASE_URL}/api/v1/analysis/${analysisId}/annotations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      annotation_text: annotationText,
      field_name: fieldName || 'clinical_impression',
    }),
  });

  if (!res.ok) {
    let msg = `Annotation failed (${res.status})`;
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  return (await res.json()) as AnnotationItem;
}
