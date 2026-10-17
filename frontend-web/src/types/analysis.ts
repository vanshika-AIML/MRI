/**
 * TypeScript interface definitions matching the FastAPI backend analysis schemas.
 */

export type SourceFormat = 'dicom' | 'nifti' | 'image' | 'png' | 'jpeg' | 'numpy';
export type SeverityLevel = 'normal' | 'low' | 'medium' | 'moderate' | 'high';
export type StageName = 'preprocessing' | 'enhancement' | 'detection';

export interface InputMetadata {
  filename: string;
  source_format: SourceFormat | string;
  dimensions: number[];
  ndim: number;
  modality: string;
  patient_id?: string | null;
  study_instance_uid?: string | null;
  series_instance_uid?: string | null;
}

export interface DetectedRegion {
  region_id: string;
  bbox: number[]; // [y_min, x_min, y_max, x_max] or 3D bounding box
  centroid: number[]; // [row, col]
  area_pixels: number;
  mean_intensity: number;
  max_intensity: number;
  anomaly_score: number;
  confidence: number;
  severity: SeverityLevel | string;
  slice_index?: number | null;
}

export interface StageResult {
  stage: StageName | string;
  success: boolean;
  duration_ms: number;
  details: Record<string, unknown>;
  error_message?: string | null;
}

export interface AnalysisOptions {
  analysis_method?: 'baseline' | 'research_flair_segmentation';
  flair_sequence_confirmed?: boolean;
  normalize?: boolean;
  normalization_method?: 'minmax' | 'zscore';
  enable_enhancement?: boolean;
  enhancement_methods?: string[];
  enable_detection?: boolean;
  detection_methods?: string[];
  confidence_threshold?: number;
  study_id?: string;
}

export interface SegmentationPrediction {
  target: string;
  modality: string;
  mask_format: string;
  mask_nifti_gz_base64: string;
  overlay_format: string;
  overlay_png_base64: string;
  preview_slice_index: number;
  mask_dimensions: number[];
  affine: number[][];
  voxel_spacing_mm: number[];
  predicted_voxels: number;
  threshold: number;
  preprocessing_version: string;
  checkpoint_sha256: string;
  input_sha256: string;
  mask_sha256: string;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: 'completed' | 'failed' | string;
  success: boolean;
  timestamp: string;
  input_metadata: InputMetadata;
  model_name: string;
  model_version: string;
  is_baseline: boolean;
  total_duration_ms: number;
  severity: SeverityLevel | string;
  overall_confidence: number;
  detected_regions_count: number;
  detected_regions: DetectedRegion[];
  prediction?: SegmentationPrediction | null;
  stage_results: StageResult[];
  summary: string;
  warnings: string[];
  error_message?: string | null;
  clinical_disclaimer: string;
}

export interface ApiError {
  error: {
    status_code: number;
    message: string;
    details?: unknown;
  };
}
