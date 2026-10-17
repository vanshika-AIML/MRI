import 'dart:convert';
import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import '../widgets/scan_preview.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme.dart';
import '../providers/analysis_provider.dart';
import '../providers/auth_provider.dart';
import '../widgets/clinical_disclaimer.dart';
import '../widgets/severity_badge.dart';

/// Mobile Results Dashboard Screen.
/// Presents executive findings, provenance metadata, radiologist annotations,
/// and mandatory clinical disclaimer.
class ResultsScreen extends StatefulWidget {
  const ResultsScreen({super.key});

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  final _annotationController = TextEditingController();
  bool _isSavingAnnotation = false;

  @override
  void dispose() {
    _annotationController.dispose();
    super.dispose();
  }

  Future<void> _addAnnotation() async {
    final text = _annotationController.text.trim();
    if (text.isEmpty) return;

    setState(() => _isSavingAnnotation = true);
    final analysis = Provider.of<AnalysisProvider>(context, listen: false);
    final ok = await analysis.addAnnotation(text);
    if (mounted) {
      setState(() => _isSavingAnnotation = false);
      if (ok) {
        _annotationController.clear();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Clinical annotation recorded in audit log.'),
            backgroundColor: Color(0xFF16A34A),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final analysis = Provider.of<AnalysisProvider>(context);
    final auth = Provider.of<AuthProvider>(context);
    final result = analysis.result;

    if (result == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Findings Dashboard')),
        body: const Center(child: Text('No analysis results available.')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Findings Dashboard'),
        actions: [
          IconButton(
            tooltip: 'Save JSON report',
            icon: const Icon(Icons.download_outlined),
            onPressed: () async {
              try {
                await FilePicker.saveFile(
                  fileName: 'mri-${result.analysisId}.json',
                  type: FileType.custom,
                  allowedExtensions: ['json'],
                  bytes: Uint8List.fromList(
                    utf8.encode(
                      const JsonEncoder.withIndent(
                        '  ',
                      ).convert(result.originalJson),
                    ),
                  ),
                );
              } catch (_) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Unable to save report. Please try again.'),
                    ),
                  );
                }
              }
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              Navigator.of(context).pop();
            },
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (analysis.selectedFile != null)
                ScanPreview(file: analysis.selectedFile!, result: result),
              if (result.prediction != null)
                OutlinedButton.icon(
                  onPressed: () async {
                    try {
                      await FilePicker.saveFile(
                        fileName: 'mri-${result.analysisId}-mask.nii.gz',
                        bytes: Uint8List.fromList(
                          base64Decode(result.prediction!.maskNiftiGzBase64),
                        ),
                      );
                    } catch (_) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Unable to save segmentation mask.'),
                          ),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.download_outlined),
                  label: const Text('Download NIfTI research mask'),
                ),
              // Top Status Header Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: ClinicalTheme.borderLight),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF0FDF4),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFFBBF7D0)),
                          ),
                          child: Text(
                            result.status.toUpperCase(),
                            style: const TextStyle(
                              color: Color(0xFF16A34A),
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFFFBEB),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFFFDE68A)),
                          ),
                          child: Text(
                            result.isBaseline
                                ? 'Baseline Engine'
                                : 'Research Model',
                            style: const TextStyle(
                              color: Color(0xFFD97706),
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      'Automated Findings Overview',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: ClinicalTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Job ID: ${result.analysisId.substring(0, 8)}... • Scan: ${result.inputMetadata.filename}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: ClinicalTheme.textMuted,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Metrics Grid (Severity, Anomaly Score, Detected Regions, Duration)
              Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: ClinicalTheme.borderLight),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Severity',
                            style: TextStyle(
                              fontSize: 11,
                              color: ClinicalTheme.textMuted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          result.prediction == null
                              ? SeverityBadgeWidget(severity: result.severity)
                              : const Text('Not assessed'),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: ClinicalTheme.borderLight),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            result.prediction == null
                                ? 'Peak Score'
                                : 'Predicted Voxels',
                            style: const TextStyle(
                              fontSize: 11,
                              color: ClinicalTheme.textMuted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            result.prediction == null
                                ? '${(result.overallConfidence * 100).toStringAsFixed(1)}%'
                                : result.prediction!.predictedVoxels.toString(),
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: ClinicalTheme.primaryBlue,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: ClinicalTheme.borderLight),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            result.prediction == null ? 'Regions' : 'Model',
                            style: const TextStyle(
                              fontSize: 11,
                              color: ClinicalTheme.textMuted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            result.prediction == null
                                ? '${result.detectedRegionsCount} detected'
                                : result.modelName,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: ClinicalTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: ClinicalTheme.borderLight),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Latency',
                            style: TextStyle(
                              fontSize: 11,
                              color: ClinicalTheme.textMuted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${result.totalDurationMs.toStringAsFixed(0)} ms',
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: ClinicalTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Summary
              if (result.summary != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Summary: ${result.summary}',
                    style: const TextStyle(
                      fontSize: 12,
                      color: ClinicalTheme.textPrimary,
                      height: 1.4,
                    ),
                  ),
                ),
              const SizedBox(height: 14),

              // Provenance & Source Immutability Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: ClinicalTheme.borderLight),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.shield_outlined,
                          size: 18,
                          color: ClinicalTheme.primaryBlue,
                        ),
                        SizedBox(width: 8),
                        Text(
                          'Provenance & Data Integrity',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: ClinicalTheme.textPrimary,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 8),
                    Text(
                      '• Original uploaded file remains immutable and protected.\n'
                      '• Derived signal outputs preserve cryptographic traceability.\n'
                      '• Model pipeline: baseline_mri_pipeline v1.0.0',
                      style: TextStyle(
                        fontSize: 11,
                        color: ClinicalTheme.textSecondary,
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Clinical Annotations & Controlled Modification
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: ClinicalTheme.borderLight),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Clinical Observations & Notes',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: ClinicalTheme.textPrimary,
                          ),
                        ),
                        Text(
                          'AUDITED TRAIL',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: ClinicalTheme.primaryBlue,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    if (analysis.annotations.isNotEmpty)
                      ...analysis.annotations.map(
                        (ann) => Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: const Color(0xFFE2E8F0)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  const Text(
                                    'RADIOLOGIST ANNOTATION (NOT MODEL)',
                                    style: TextStyle(
                                      fontSize: 9,
                                      fontWeight: FontWeight.bold,
                                      color: Color(0xFF4F46E5),
                                    ),
                                  ),
                                  Text(
                                    'v${ann.version}',
                                    style: const TextStyle(
                                      fontSize: 10,
                                      color: ClinicalTheme.textMuted,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                ann.annotationText,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: ClinicalTheme.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      )
                    else
                      const Text(
                        'No annotations recorded yet.',
                        style: TextStyle(
                          fontSize: 12,
                          color: ClinicalTheme.textMuted,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    const SizedBox(height: 10),

                    if (auth.isRadiologist) ...[
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _annotationController,
                              style: const TextStyle(fontSize: 13),
                              decoration: const InputDecoration(
                                hintText: 'Add clinical observation note...',
                                contentPadding: EdgeInsets.symmetric(
                                  horizontal: 12,
                                  vertical: 10,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: _isSavingAnnotation
                                ? null
                                : _addAnnotation,
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 12,
                              ),
                            ),
                            child: _isSavingAnnotation
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(
                                        Colors.white,
                                      ),
                                    ),
                                  )
                                : const Text('Add Note'),
                          ),
                        ],
                      ),
                    ] else ...[
                      Text(
                        auth.isAuthenticated
                            ? 'Viewer accounts are read-only. Sign in as Radiologist or Admin to attach audited clinical notes.'
                            : 'Sign in as Radiologist or Admin to record audited clinical notes.',
                        style: const TextStyle(
                          fontSize: 11,
                          color: ClinicalTheme.textMuted,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Mandatory Clinical Disclaimer
              ClinicalDisclaimerWidget(customText: result.clinicalDisclaimer),
              const SizedBox(height: 20),

              // Bottom Button
              ElevatedButton.icon(
                icon: const Icon(Icons.arrow_back),
                label: const Text('Analyze Another Scan'),
                onPressed: () {
                  analysis.reset();
                  Navigator.of(context).pop();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
