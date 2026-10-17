/// Core constants for the MRI Analysis Flutter Mobile Application.
library;

class AppConstants {
  // Default API base URL (can be customized via settings or build environment)
  // For Android emulator: 10.0.2.2 maps to host 127.0.0.1
  static const String defaultBaseUrl = 'http://10.0.2.2:8000';
  static const String defaultIosBaseUrl = 'http://127.0.0.1:8000';

  // API Route Paths matching FastAPI backend
  static const String healthPath = '/api/v1/health';
  static const String analysisPath = '/api/v1/analysis';
  static const String authRegisterPath = '/api/v1/auth/register';
  static const String authLoginPath = '/api/v1/auth/login';
  static const String authRefreshPath = '/api/v1/auth/refresh';
  static const String authLogoutPath = '/api/v1/auth/logout';
  static const String authMePath = '/api/v1/auth/me';

  // Supported File Extensions matching ML pipeline & backend validation
  static const List<String> supportedExtensions = [
    'dcm',
    'nii',
    'gz', // for .nii.gz
    'png',
    'jpg',
    'jpeg',
    'npy',
    'npz',
  ];

  // Maximum file upload size: 100 MB
  static const int maxFileSizeInBytes = 100 * 1024 * 1024;

  // Mandatory Clinical Disclaimer
  static const String mandatoryDisclaimer =
      'RESEARCH-ONLY DISCLAIMER: This system provides experimental image processing, '
      'heuristic indicators, or segmentation predictions for technical research only. '
      'It does NOT provide a clinical diagnosis, medical opinion, or confirmed lesion '
      'classification. Model masks and scores are not clinical probabilities and may '
      'be wrong. Outputs require independent review by a qualified medical professional '
      'and must not guide patient care.';
}
