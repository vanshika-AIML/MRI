/// Annotation model for controlled radiologist modifications & notes.
library;

class AnnotationItem {
  final String id;
  final String analysisId;
  final String userId;
  final String annotationText;
  final String? fieldName;
  final bool isOriginal;
  final int version;
  final String createdAt;

  AnnotationItem({
    required this.id,
    required this.analysisId,
    required this.userId,
    required this.annotationText,
    this.fieldName,
    required this.isOriginal,
    required this.version,
    required this.createdAt,
  });

  factory AnnotationItem.fromJson(Map<String, dynamic> json) {
    return AnnotationItem(
      id: json['id'] as String? ?? '',
      analysisId: json['analysis_id'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      annotationText: json['annotation_text'] as String? ?? '',
      fieldName: json['field_name'] as String?,
      isOriginal: json['is_original'] as bool? ?? false,
      version: (json['version'] as num?)?.toInt() ?? 1,
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}
