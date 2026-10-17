import 'package:flutter_test/flutter_test.dart';
import 'package:mri_analysis_mobile/models/user.dart';
import 'package:mri_analysis_mobile/models/analysis.dart';
import 'package:mri_analysis_mobile/models/annotation.dart';

void main() {
  group('Mobile Model Parsing Tests', () {
    test('UserPublic parses role and flags correctly', () {
      final json = {
        'id': 'usr-1234',
        'email': 'radiologist@hospital.org',
        'username': 'dr_smith',
        'full_name': 'Dr. Jane Smith',
        'role': 'radiologist',
        'profession': 'radiologist',
        'is_active': true,
        'is_verified': true,
      };

      final user = UserPublic.fromJson(json);
      expect(user.id, 'usr-1234');
      expect(user.email, 'radiologist@hospital.org');
      expect(user.role, UserRole.radiologist);
      expect(user.profession, 'radiologist');
      expect(user.isActive, true);
      expect(user.isVerified, true);
    });

    test('AnalysisResponse parses findings and disclaimer', () {
      final json = {
        'analysis_id': 'job-abc-999',
        'status': 'completed',
        'success': true,
        'timestamp': '2026-10-13T12:00:00Z',
        'input_metadata': {
          'filename': 'scan_t1.dcm',
          'source_format': 'dicom',
          'dimensions': [256, 256],
          'ndim': 2,
        },
        'model_name': 'baseline_mri_pipeline',
        'model_version': '1.0.0',
        'is_baseline': true,
        'total_duration_ms': 120.5,
        'severity': 'low',
        'overall_confidence': 0.65,
        'detected_regions_count': 1,
        'detected_regions': [
          {
            'region_id': 'reg_0',
            'bbox': [10, 10, 30, 30],
            'area_pixels': 200,
            'mean_intensity': 180.0,
            'max_intensity': 220.0,
            'anomaly_score': 0.65,
            'confidence': 0.65,
            'severity': 'low',
          },
        ],
        'warnings': [],
        'clinical_disclaimer': 'DISCLAIMER: Non-clinical tool.',
      };

      final response = AnalysisResponse.fromJson(json);
      expect(response.analysisId, 'job-abc-999');
      expect(response.isBaseline, true);
      expect(response.detectedRegionsCount, 1);
      expect(response.detectedRegions.first.severity, 'low');
      expect(response.clinicalDisclaimer, contains('DISCLAIMER'));
    });

    test(
      'AnalysisResponse parses research segmentation provenance and preview',
      () {
        final response = AnalysisResponse.fromJson({
          'analysis_id': 'research-123',
          'status': 'completed',
          'success': true,
          'timestamp': '2026-10-16T12:00:00Z',
          'input_metadata': {
            'filename': 'research_flair.nii.gz',
            'source_format': 'nifti',
            'dimensions': [24, 20, 5],
            'ndim': 3,
            'modality': 'FLAIR',
          },
          'model_name': 'msd_flair_whole_tumor_unet',
          'model_version': 'checkpoint',
          'is_baseline': false,
          'total_duration_ms': 120.5,
          'severity': 'not_assessed',
          'overall_confidence': 0,
          'detected_regions_count': 0,
          'detected_regions': [],
          'prediction': {
            'overlay_format': 'image/png',
            'overlay_png_base64': 'cG5n',
            'mask_format': 'application/gzip+nifti',
            'mask_nifti_gz_base64': 'bWFzaw==',
            'mask_sha256': 'abc',
            'preview_slice_index': 3,
            'mask_dimensions': [24, 20, 5],
            'predicted_voxels': 9,
            'voxel_spacing_mm': [1.5, 2.0, 2.5],
          },
          'warnings': ['Research only'],
          'clinical_disclaimer': 'Research only',
        });

        expect(response.isBaseline, false);
        expect(response.prediction?.previewSliceIndex, 3);
        expect(response.prediction?.predictedVoxels, 9);
        expect(response.prediction?.voxelSpacingMm, [1.5, 2.0, 2.5]);
      },
    );

    test('Missing severity is inconclusive rather than normal', () {
      final response = AnalysisResponse.fromJson({
        'input_metadata': <String, dynamic>{},
        'detected_regions': [],
        'warnings': [],
      });
      expect(response.severity, 'not_assessed');
    });

    test('AnnotationItem parses version and text', () {
      final json = {
        'id': 'ann-456',
        'analysis_id': 'job-abc-999',
        'user_id': 'usr-1234',
        'annotation_text': 'Confirmed motion artifact in sagittal plane.',
        'field_name': 'clinical_impression',
        'is_original': false,
        'version': 2,
        'created_at': '2026-10-13T12:05:00Z',
      };

      final ann = AnnotationItem.fromJson(json);
      expect(ann.id, 'ann-456');
      expect(ann.version, 2);
      expect(ann.isOriginal, false);
      expect(ann.annotationText, contains('Confirmed motion artifact'));
    });
  });
}
