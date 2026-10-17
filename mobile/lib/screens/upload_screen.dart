import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../providers/analysis_provider.dart';
import '../providers/auth_provider.dart';
import 'login_screen.dart';
import 'results_screen.dart';
import 'settings_screen.dart';

/// Upload & MRI Scan Selection Screen.
/// Provides format validation, parameter tuning, and execution trigger.
class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  bool _showAdvancedParams = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AnalysisProvider>(context, listen: false).checkConnection();
    });
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: AppConstants.supportedExtensions,
    );

    if (result != null && result.files.single.path != null) {
      final file = File(result.files.single.path!);
      final size = await file.length();

      if (size > AppConstants.maxFileSizeInBytes) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('File size exceeds the 100MB limit.'),
              backgroundColor: Color(0xFFDC2626),
            ),
          );
        }
        return;
      }

      if (mounted) {
        Provider.of<AnalysisProvider>(
          context,
          listen: false,
        ).setSelectedFile(file);
      }
    }
  }

  Future<void> _executeAnalysis() async {
    final analysis = Provider.of<AnalysisProvider>(context, listen: false);
    final success = await analysis.executeAnalysis();

    if (success && mounted) {
      Navigator.of(
        context,
      ).push(MaterialPageRoute(builder: (_) => const ResultsScreen()));
    }
  }

  @override
  Widget build(BuildContext context) {
    final analysis = Provider.of<AnalysisProvider>(context);
    final auth = Provider.of<AuthProvider>(context);

    if (auth.isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!auth.isAuthenticated) {
      return const LoginScreen();
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('MRI Research'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () {
              Navigator.of(
                context,
              ).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
            },
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFBFDBFE)),
                ),
                child: Text(
                  auth.currentUser?.role.name.toUpperCase() ?? 'USER',
                  style: const TextStyle(
                    color: Color(0xFF1D4ED8),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Connection Status Indicator
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: analysis.isBackendConnected == true
                          ? const Color(0xFF16A34A)
                          : analysis.isBackendConnected == false
                          ? const Color(0xFFDC2626)
                          : const Color(0xFF94A3B8),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    analysis.isBackendConnected == true
                        ? 'Backend Ready (API v1)'
                        : analysis.isBackendConnected == false
                        ? 'Backend Server Offline'
                        : 'Checking API Connection...',
                    style: const TextStyle(
                      fontSize: 12,
                      color: ClinicalTheme.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Title Card
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
                    Text(
                      'MRI Research Workspace',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: ClinicalTheme.textPrimary,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Choose baseline heuristic processing or experimental FLAIR whole-tumor segmentation. All outputs are research-only and not for clinical decisions.',
                      style: TextStyle(
                        fontSize: 13,
                        color: ClinicalTheme.textSecondary,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // File Selection Box
              InkWell(
                onTap: analysis.isLoading ? null : _pickFile,
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    vertical: 32,
                    horizontal: 20,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: analysis.selectedFile != null
                          ? ClinicalTheme.primaryBlue
                          : const Color(0xFFCBD5E1),
                      width: 1.5,
                    ),
                  ),
                  child: Column(
                    children: [
                      Icon(
                        analysis.selectedFile != null
                            ? Icons.check_circle_outline
                            : Icons.cloud_upload_outlined,
                        size: 44,
                        color: analysis.selectedFile != null
                            ? ClinicalTheme.primaryBlue
                            : const Color(0xFF64748B),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        analysis.selectedFile != null
                            ? analysis.selectedFile!.path
                                  .split(Platform.pathSeparator)
                                  .last
                            : 'Tap to select an MRI scan file',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: analysis.selectedFile != null
                              ? ClinicalTheme.primaryBlue
                              : ClinicalTheme.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Supports DICOM (.dcm), NIfTI (.nii, .nii.gz), PNG, JPEG, NumPy (.npy)',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 11,
                          color: ClinicalTheme.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              DropdownButtonFormField<String>(
                initialValue: analysis.analysisMethod,
                decoration: const InputDecoration(
                  labelText: 'Analysis method',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'baseline',
                    child: Text('Baseline heuristic'),
                  ),
                  DropdownMenuItem(
                    value: 'research_flair_segmentation',
                    child: Text('Research FLAIR mask'),
                  ),
                ],
                onChanged: (value) {
                  if (value != null) analysis.setAnalysisMethod(value);
                },
              ),
              if (analysis.analysisMethod == 'research_flair_segmentation')
                Column(
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: Text(
                        'Requires a 3D FLAIR NIfTI volume (.nii or .nii.gz). Sequence and anatomy cannot be verified from NIfTI voxel data. Research-only; not for patient care.',
                        style: TextStyle(
                          color: Color(0xFFB45309),
                          fontSize: 12,
                        ),
                      ),
                    ),
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: analysis.flairSequenceConfirmed,
                      onChanged: (value) =>
                          analysis.confirmFlairSequence(value ?? false),
                      title: const Text(
                        'I confirm this is a brain FLAIR volume',
                        style: TextStyle(fontSize: 13),
                      ),
                      subtitle: const Text(
                        'Self-declared; not independently verified.',
                        style: TextStyle(fontSize: 11),
                      ),
                    ),
                  ],
                ),
              const SizedBox(height: 16),

              // Advanced Parameters Toggle
              Theme(
                data: Theme.of(
                  context,
                ).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  title: const Text(
                    'Pipeline Analysis Settings',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: ClinicalTheme.textPrimary,
                    ),
                  ),
                  subtitle: const Text(
                    'Configure normalization and contrast enhancement algorithms',
                    style: TextStyle(
                      fontSize: 12,
                      color: ClinicalTheme.textMuted,
                    ),
                  ),
                  initiallyExpanded: _showAdvancedParams,
                  onExpansionChanged: (exp) =>
                      setState(() => _showAdvancedParams = exp),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: ClinicalTheme.borderLight),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: const Text(
                              'Intensity Normalization',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            subtitle: const Text(
                              'Scales intensity distribution to [0, 1]',
                              style: TextStyle(
                                fontSize: 11,
                                color: ClinicalTheme.textMuted,
                              ),
                            ),
                            value: analysis.normalize,
                            onChanged: analysis.analysisMethod == 'baseline'
                                ? (val) =>
                                      analysis.updateParameters(normalize: val)
                                : null,
                          ),
                          const Divider(),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: const Text(
                              'Soft-Tissue Enhancement (CLAHE)',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            subtitle: const Text(
                              'Adaptive histogram equalization for local contrast',
                              style: TextStyle(
                                fontSize: 11,
                                color: ClinicalTheme.textMuted,
                              ),
                            ),
                            value: analysis.enableEnhancement,
                            onChanged: analysis.analysisMethod == 'baseline'
                                ? (val) => analysis.updateParameters(
                                    enableEnhancement: val,
                                  )
                                : null,
                          ),
                          const Divider(),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: const Text(
                              'Abnormality Detection',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            subtitle: const Text(
                              'Heuristic thresholding for hyperintensity deviations',
                              style: TextStyle(
                                fontSize: 11,
                                color: ClinicalTheme.textMuted,
                              ),
                            ),
                            value: analysis.enableDetection,
                            onChanged: analysis.analysisMethod == 'baseline'
                                ? (val) => analysis.updateParameters(
                                    enableDetection: val,
                                  )
                                : null,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Error Banner
              if (analysis.errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFEF2F2),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFFECACA)),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.error_outline,
                        color: Color(0xFFDC2626),
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          analysis.errorMessage!,
                          style: const TextStyle(
                            color: Color(0xFFB91C1C),
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Run Analysis Action Button
              ElevatedButton(
                onPressed: (analysis.isLoading || analysis.selectedFile == null)
                    ? null
                    : _executeAnalysis,
                child: analysis.isLoading
                    ? const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Colors.white,
                              ),
                            ),
                          ),
                          SizedBox(width: 10),
                          Text('Running AI Inference Pipeline...'),
                        ],
                      )
                    : const Text('Run MRI Analysis'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
