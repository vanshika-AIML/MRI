/// Analysis models matching backend Pydantic AnalysisResponse schema.
library;

class DetectedRegion {
  final String regionId;
  final List<dynamic> bbox;
  final List<dynamic>? centroid;
  final int areaPixels;
  final double meanIntensity;
  final double maxIntensity;
  final double anomalyScore;
  final double confidence;
  final String severity;

  DetectedRegion({
    required this.regionId,
    required this.bbox,
    this.centroid,
    required this.areaPixels,
    required this.meanIntensity,
    required this.maxIntensity,
    required this.anomalyScore,
    required this.confidence,
    required this.severity,
  });

  factory DetectedRegion.fromJson(Map<String, dynamic> json) {
    return DetectedRegion(
      regionId: json['region_id'] as String? ?? '',
      bbox: (json['bbox'] as List<dynamic>?) ?? [],
      centroid: json['centroid'] as List<dynamic>?,
      areaPixels: (json['area_pixels'] as num?)?.toInt() ?? 0,
      meanIntensity: (json['mean_intensity'] as num?)?.toDouble() ?? 0.0,
      maxIntensity: (json['max_intensity'] as num?)?.toDouble() ?? 0.0,
      anomalyScore: (json['anomaly_score'] as num?)?.toDouble() ?? 0.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      severity: json['severity'] as String? ?? 'low',
    );
  }
}

class InputMetadata {
  final String filename;
  final String sourceFormat;
  final List<int> dimensions;
  final int ndim;
  final String? modality;
  final String? patientId;

  InputMetadata({
    required this.filename,
    required this.sourceFormat,
    required this.dimensions,
    required this.ndim,
    this.modality,
    this.patientId,
  });

  factory InputMetadata.fromJson(Map<String, dynamic> json) {
    return InputMetadata(
      filename: json['filename'] as String? ?? '',
      sourceFormat: json['source_format'] as String? ?? '',
      dimensions: ((json['dimensions'] as List<dynamic>?) ?? [])
          .map((e) => (e as num).toInt())
          .toList(),
      ndim: (json['ndim'] as num?)?.toInt() ?? 2,
      modality: json['modality'] as String?,
      patientId: json['patient_id'] as String?,
    );
  }
}

class SegmentationPrediction {
  final String overlayFormat;
  final String overlayPngBase64;
  final String maskFormat;
  final String maskNiftiGzBase64;
  final String maskSha256;
  final int previewSliceIndex;
  final List<int> maskDimensions;
  final int predictedVoxels;
  final List<double> voxelSpacingMm;

  SegmentationPrediction({
    required this.overlayFormat,
    required this.overlayPngBase64,
    required this.maskFormat,
    required this.maskNiftiGzBase64,
    required this.maskSha256,
    required this.previewSliceIndex,
    required this.maskDimensions,
    required this.predictedVoxels,
    required this.voxelSpacingMm,
  });

  factory SegmentationPrediction.fromJson(Map<String, dynamic> json) {
    return SegmentationPrediction(
      overlayFormat: json['overlay_format'] as String? ?? 'image/png',
      overlayPngBase64: json['overlay_png_base64'] as String? ?? '',
      maskFormat: json['mask_format'] as String? ?? 'application/gzip+nifti',
      maskNiftiGzBase64: json['mask_nifti_gz_base64'] as String? ?? '',
      maskSha256: json['mask_sha256'] as String? ?? '',
      previewSliceIndex: (json['preview_slice_index'] as num?)?.toInt() ?? 0,
      maskDimensions: ((json['mask_dimensions'] as List<dynamic>?) ?? [])
          .map((e) => (e as num).toInt())
          .toList(),
      predictedVoxels: (json['predicted_voxels'] as num?)?.toInt() ?? 0,
      voxelSpacingMm: ((json['voxel_spacing_mm'] as List<dynamic>?) ?? [])
          .map((e) => (e as num).toDouble())
          .toList(),
    );
  }
}

class AnalysisResponse {
  final Map<String, dynamic> originalJson;
  final String analysisId;
  final String status;
  final bool success;
  final String timestamp;
  final InputMetadata inputMetadata;
  final String modelName;
  final String modelVersion;
  final bool isBaseline;
  final double totalDurationMs;
  final String severity;
  final double overallConfidence;
  final int detectedRegionsCount;
  final List<DetectedRegion> detectedRegions;
  final SegmentationPrediction? prediction;
  final String? summary;
  final List<String> warnings;
  final String clinicalDisclaimer;

  AnalysisResponse({
    this.originalJson = const {},
    required this.analysisId,
    required this.status,
    required this.success,
    required this.timestamp,
    required this.inputMetadata,
    required this.modelName,
    required this.modelVersion,
    required this.isBaseline,
    required this.totalDurationMs,
    required this.severity,
    required this.overallConfidence,
    required this.detectedRegionsCount,
    required this.detectedRegions,
    this.prediction,
    this.summary,
    required this.warnings,
    required this.clinicalDisclaimer,
  });

  factory AnalysisResponse.fromJson(Map<String, dynamic> json) {
    final regionsJson = (json['detected_regions'] as List<dynamic>?) ?? [];
    final warningsJson = (json['warnings'] as List<dynamic>?) ?? [];

    return AnalysisResponse(
      originalJson: Map<String, dynamic>.unmodifiable(json),
      analysisId: json['analysis_id'] as String? ?? '',
      status: json['status'] as String? ?? '',
      success: json['success'] as bool? ?? false,
      timestamp: json['timestamp'] as String? ?? '',
      inputMetadata: InputMetadata.fromJson(
        json['input_metadata'] as Map<String, dynamic>? ?? {},
      ),
      modelName: json['model_name'] as String? ?? 'baseline_pipeline',
      modelVersion: json['model_version'] as String? ?? '1.0.0',
      isBaseline: json['is_baseline'] as bool? ?? true,
      totalDurationMs: (json['total_duration_ms'] as num?)?.toDouble() ?? 0.0,
      severity: json['severity'] as String? ?? 'not_assessed',
      overallConfidence:
          (json['overall_confidence'] as num?)?.toDouble() ?? 0.0,
      detectedRegionsCount:
          (json['detected_regions_count'] as num?)?.toInt() ?? 0,
      detectedRegions: regionsJson
          .map((e) => DetectedRegion.fromJson(e as Map<String, dynamic>))
          .toList(),
      prediction: json['prediction'] is Map<String, dynamic>
          ? SegmentationPrediction.fromJson(
              json['prediction'] as Map<String, dynamic>,
            )
          : null,
      summary: json['summary'] as String?,
      warnings: warningsJson.map((e) => e.toString()).toList(),
      clinicalDisclaimer: json['clinical_disclaimer'] as String? ?? '',
    );
  }
}
