import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme.dart';
import '../providers/analysis_provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';
import 'login_screen.dart';

/// Mobile Settings & Configuration Screen.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _urlController.text = ApiClient().baseUrl;
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _saveUrl() async {
    final url = _urlController.text.trim();
    if (url.isNotEmpty) {
      try {
        await ApiClient().setBaseUrl(url);
      } on FormatException catch (error) {
        if (mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text(error.message)));
        }
        return;
      }
      if (!mounted) return;
      Provider.of<AuthProvider>(context, listen: false).initialize();
      Provider.of<AnalysisProvider>(context, listen: false).checkConnection();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('API Server URL updated.'),
          backgroundColor: Color(0xFF16A34A),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings & Configuration')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Account Profile Section
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
                  const Text(
                    'User Account',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: ClinicalTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (auth.isAuthenticated && auth.currentUser != null) ...[
                    Row(
                      children: [
                        CircleAvatar(
                          backgroundColor: ClinicalTheme.primaryBlue,
                          child: Text(
                            auth.currentUser!.username
                                .substring(0, 1)
                                .toUpperCase(),
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                auth.currentUser!.fullName ??
                                    auth.currentUser!.username,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                              Text(
                                auth.currentUser!.email,
                                style: const TextStyle(
                                  color: ClinicalTheme.textMuted,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEFF6FF),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFFBFDBFE)),
                          ),
                          child: Text(
                            auth.currentUser!.role.name.toUpperCase(),
                            style: const TextStyle(
                              color: Color(0xFF1D4ED8),
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.logout, size: 16),
                      label: const Text('Sign Out'),
                      onPressed: () async {
                        await auth.logout();
                      },
                    ),
                  ] else ...[
                    const Text(
                      'Currently in guest viewer mode.',
                      style: TextStyle(
                        fontSize: 13,
                        color: ClinicalTheme.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      onPressed: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => const LoginScreen(),
                          ),
                        );
                      },
                      child: const Text('Sign In or Register'),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),

            // API Server Configuration Section
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
                  const Text(
                    'Backend API Server URL',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: ClinicalTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Configure target FastAPI endpoint (10.0.2.2 for Android emulator, 127.0.0.1 for iOS simulator).',
                    style: TextStyle(
                      fontSize: 11,
                      color: ClinicalTheme.textMuted,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _urlController,
                          decoration: const InputDecoration(
                            hintText: 'http://10.0.2.2:8000',
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: _saveUrl,
                        child: const Text('Save'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Platform and Build Info
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
                    'System Diagnostics',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: ClinicalTheme.textPrimary,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    '• Client: Flutter Mobile App (Phase 9 Cross-Platform)\n'
                    '• Pipeline: FastAPI + Python ML Backend\n'
                    '• Security: JWT Bearer + PBKDF2/Bcrypt + Audit Trail\n'
                    '• Architecture: Provider State Management',
                    style: TextStyle(
                      fontSize: 11,
                      color: ClinicalTheme.textSecondary,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
