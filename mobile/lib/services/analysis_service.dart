import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../core/constants.dart';
import '../models/analysis.dart';
import '../models/annotation.dart';
import 'api_client.dart';

/// Service managing MRI scan inference requests,
/// backend health checks, and radiologist annotations.
class AnalysisService {
  final ApiClient _client = ApiClient();

  Future<bool> checkHealth() async {
    try {
      final response = await _client.get(AppConstants.healthPath, auth: false);
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<AnalysisResponse> runAnalysis({
    required File file,
    bool normalize = true,
    String? normalizationMethod,
    bool enableEnhancement = true,
    List<String>? enhancementMethods,
    bool enableDetection = true,
    List<String>? detectionMethods,
    double confidenceThreshold = 0.5,
    String analysisMethod = 'baseline',
    bool flairSequenceConfirmed = false,
  }) async {
    final uri = Uri.parse('${_client.baseUrl}${AppConstants.analysisPath}');
    final request = http.MultipartRequest('POST', uri);

    // Attach Bearer token if logged in
    final token = await _client.getAccessToken();
    if (token != null && token.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $token';
    }

    // Attach form fields
    request.fields['normalize'] = normalize.toString();
    if (normalizationMethod != null) {
      request.fields['normalization_method'] = normalizationMethod;
    }
    request.fields['enable_enhancement'] = enableEnhancement.toString();
    if (enhancementMethods != null && enhancementMethods.isNotEmpty) {
      request.fields['enhancement_methods'] = enhancementMethods.join(',');
    }
    request.fields['enable_detection'] = enableDetection.toString();
    if (detectionMethods != null && detectionMethods.isNotEmpty) {
      request.fields['detection_methods'] = detectionMethods.join(',');
    }
    request.fields['confidence_threshold'] = confidenceThreshold.toString();
    request.fields['analysis_method'] = analysisMethod;
    request.fields['flair_sequence_confirmed'] = flairSequenceConfirmed
        .toString();

    // Attach file
    final multipartFile = await http.MultipartFile.fromPath('file', file.path);
    request.files.add(multipartFile);

    final streamedResponse = await request.send().timeout(
      const Duration(minutes: 2),
    );
    final response = await http.Response.fromStream(
      streamedResponse,
    ).timeout(const Duration(minutes: 2));

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      if (json["success"] != true) {
        throw Exception(
          json["error_message"] ??
              "The analysis pipeline failed. Please check the input and settings.",
        );
      }
      return AnalysisResponse.fromJson(json);
    } else {
      String errorMsg = 'Analysis failed (${response.statusCode})';
      try {
        final errJson = jsonDecode(response.body);
        if (errJson is Map) {
          if (errJson['error'] != null && errJson['error']['message'] != null) {
            errorMsg = errJson['error']['message'].toString();
          } else if (errJson['detail'] != null) {
            errorMsg = errJson['detail'].toString();
          }
        }
      } catch (_) {}
      throw Exception(errorMsg);
    }
  }

  Future<List<AnnotationItem>> getAnnotations(String analysisId) async {
    try {
      final response = await _client.get(
        '${AppConstants.analysisPath}/$analysisId/annotations',
        auth: true,
      );
      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list
            .map((e) => AnnotationItem.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  Future<AnnotationItem> createAnnotation({
    required String analysisId,
    required String text,
    String? fieldName,
  }) async {
    final response = await _client.post(
      '${AppConstants.analysisPath}/$analysisId/annotations',
      body: {
        'annotation_text': text.trim(),
        'field_name': fieldName ?? 'clinical_impression',
      },
      auth: true,
    );

    if (response.statusCode == 201) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return AnnotationItem.fromJson(json);
    } else {
      throw Exception('Failed to save annotation (${response.statusCode})');
    }
  }
}
