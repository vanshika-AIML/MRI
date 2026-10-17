import 'dart:io';
import 'package:flutter/material.dart';
import '../models/analysis.dart';
import '../models/annotation.dart';
import '../services/analysis_service.dart';

/// State provider managing MRI scan selection, execution parameters,
/// inference status, results dashboard data, and annotations.
class AnalysisProvider with ChangeNotifier {
  final AnalysisService _analysisService = AnalysisService();

  File? _selectedFile;
  bool _isLoading = false;
  AnalysisResponse? _result;
  String? _errorMessage;
  bool? _isBackendConnected;
  List<AnnotationItem> _annotations = [];

  // Configurable pipeline parameters
  bool _normalize = true;
  String _normalizationMethod = 'minmax';
  bool _enableEnhancement = true;
  List<String> _enhancementMethods = ['clahe'];
  bool _enableDetection = true;
  List<String> _detectionMethods = ['intensity_anomaly'];
  double _confidenceThreshold = 0.5;
  String _analysisMethod = 'baseline';
  bool _flairSequenceConfirmed = false;

  File? get selectedFile => _selectedFile;
  bool get isLoading => _isLoading;
  AnalysisResponse? get result => _result;
  String? get errorMessage => _errorMessage;
  bool? get isBackendConnected => _isBackendConnected;
  List<AnnotationItem> get annotations => _annotations;

  bool get normalize => _normalize;
  String get normalizationMethod => _normalizationMethod;
  bool get enableEnhancement => _enableEnhancement;
  List<String> get enhancementMethods => _enhancementMethods;
  bool get enableDetection => _enableDetection;
  List<String> get detectionMethods => _detectionMethods;
  double get confidenceThreshold => _confidenceThreshold;
  String get analysisMethod => _analysisMethod;
  bool get flairSequenceConfirmed => _flairSequenceConfirmed;

  void setAnalysisMethod(String value) {
    _analysisMethod = value;
    _flairSequenceConfirmed = false;
    _errorMessage = null;
    notifyListeners();
  }

  void confirmFlairSequence(bool confirmed) {
    _flairSequenceConfirmed = confirmed;
    notifyListeners();
  }

  Future<void> checkConnection() async {
    _isBackendConnected = await _analysisService.checkHealth();
    notifyListeners();
  }

  void setSelectedFile(File file) {
    _selectedFile = file;
    _errorMessage = null;
    notifyListeners();
  }

  void updateParameters({
    bool? normalize,
    String? normalizationMethod,
    bool? enableEnhancement,
    List<String>? enhancementMethods,
    bool? enableDetection,
    List<String>? detectionMethods,
    double? confidenceThreshold,
  }) {
    if (normalize != null) _normalize = normalize;
    if (normalizationMethod != null) _normalizationMethod = normalizationMethod;
    if (enableEnhancement != null) _enableEnhancement = enableEnhancement;
    if (enhancementMethods != null) _enhancementMethods = enhancementMethods;
    if (enableDetection != null) _enableDetection = enableDetection;
    if (detectionMethods != null) _detectionMethods = detectionMethods;
    if (confidenceThreshold != null) _confidenceThreshold = confidenceThreshold;
    notifyListeners();
  }

  Future<bool> executeAnalysis() async {
    if (_selectedFile == null) {
      _errorMessage = 'Please select an MRI scan file first.';
      notifyListeners();
      return false;
    }
    if (_analysisMethod == 'research_flair_segmentation' &&
        !(_selectedFile!.path.toLowerCase().endsWith('.nii') ||
            _selectedFile!.path.toLowerCase().endsWith('.nii.gz'))) {
      _errorMessage =
          'Research segmentation requires a FLAIR NIfTI volume (.nii or .nii.gz).';
      notifyListeners();
      return false;
    }
    if (_analysisMethod == 'research_flair_segmentation' &&
        !_flairSequenceConfirmed) {
      _errorMessage =
          'Confirm that this is a brain FLAIR volume before running research segmentation.';
      notifyListeners();
      return false;
    }

    _isLoading = true;
    _errorMessage = null;
    _result = null;
    _annotations = [];
    notifyListeners();

    try {
      _result = await _analysisService.runAnalysis(
        file: _selectedFile!,
        normalize: _normalize,
        normalizationMethod: _normalizationMethod,
        enableEnhancement: _enableEnhancement,
        enhancementMethods: _enhancementMethods,
        enableDetection: _enableDetection,
        detectionMethods: _detectionMethods,
        confidenceThreshold: _confidenceThreshold,
        analysisMethod: _analysisMethod,
        flairSequenceConfirmed: _flairSequenceConfirmed,
      );

      if (_result != null) {
        _annotations = await _analysisService.getAnnotations(
          _result!.analysisId,
        );
      }

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> addAnnotation(String text) async {
    if (_result == null || text.trim().isEmpty) return false;

    try {
      final created = await _analysisService.createAnnotation(
        analysisId: _result!.analysisId,
        text: text.trim(),
      );
      _annotations.add(created);
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  void reset() {
    _selectedFile = null;
    _analysisMethod = 'baseline';
    _result = null;
    _errorMessage = null;
    _isLoading = false;
    _annotations = [];
    notifyListeners();
  }
}
