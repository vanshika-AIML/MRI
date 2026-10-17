import 'dart:io';
import 'dart:async';
import 'package:provider/provider.dart';
import 'package:mri_analysis_mobile/providers/analysis_provider.dart';
import 'package:mri_analysis_mobile/providers/auth_provider.dart';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mri_analysis_mobile/main.dart';
import 'package:mri_analysis_mobile/models/user.dart';
import 'package:mri_analysis_mobile/core/constants.dart';
import 'package:mri_analysis_mobile/screens/login_screen.dart';
import 'package:mri_analysis_mobile/screens/settings_screen.dart';
import 'package:mri_analysis_mobile/screens/upload_screen.dart';

class _AuthenticatedTestUser extends AuthProvider {
  @override
  bool get isAuthenticated => true;

  @override
  bool get isLoading => false;

  @override
  UserPublic? get currentUser => UserPublic(
    id: 'test-user',
    email: 'test@example.com',
    username: 'tester',
    role: UserRole.viewer,
    profession: 'viewer',
    isActive: true,
    isVerified: false,
  );
}

Widget _authenticatedUploadApp() => MultiProvider(
  providers: [
    ChangeNotifierProvider<AuthProvider>(
      create: (_) => _AuthenticatedTestUser(),
    ),
    ChangeNotifierProvider(create: (_) => AnalysisProvider()),
  ],
  child: const MaterialApp(home: UploadScreen()),
);

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets(
    'App opens on sign-in and does not expose upload while signed out',
    (tester) async {
      await tester.pumpWidget(const MriAnalysisApp());
      await tester.pumpAndSettle();
      expect(find.byType(LoginScreen), findsOneWidget);
      expect(find.byType(UploadScreen), findsNothing);
      expect(find.text('MRI Research Workspace'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Authenticated user can navigate from upload to settings', (
    tester,
  ) async {
    await tester.pumpWidget(_authenticatedUploadApp());
    await tester.pumpAndSettle();
    expect(find.byType(UploadScreen), findsOneWidget);
    expect(find.text('MRI Research'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.settings_outlined));
    await tester.pumpAndSettle();
    expect(find.byType(SettingsScreen), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Research analysis selection is explicit and labeled nonclinical',
    (tester) async {
      await tester.pumpWidget(_authenticatedUploadApp());
      await tester.pumpAndSettle();

      final selector = find.byType(DropdownButtonFormField<String>);
      await tester.tap(selector);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Research FLAIR mask').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('I confirm this is a brain FLAIR volume'));
      await tester.pumpAndSettle();

      final provider = tester
          .element(find.byType(UploadScreen))
          .read<AnalysisProvider>();
      expect(provider.analysisMethod, 'research_flair_segmentation');
      expect(provider.flairSequenceConfirmed, isTrue);
      expect(
        find.textContaining('Research-only; not for patient care.'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('File picker preserves MRI filters and selects a scan', (
    tester,
  ) async {
    final directory = Directory.systemTemp.createTempSync('mri-picker-test-');
    final scan = File('${directory.path}${Platform.pathSeparator}scan.npy')
      ..writeAsBytesSync([1, 2, 3]);
    addTearDown(() => directory.deleteSync(recursive: true));

    const channel = MethodChannel('miguelruivo.flutter.plugins.filepicker');
    MethodCall? pickerCall;
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel, (
      call,
    ) async {
      pickerCall = call;
      return [
        {'name': 'scan.npy', 'path': scan.path, 'size': 3},
      ];
    });
    addTearDown(
      () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        channel,
        null,
      ),
    );

    await tester.pumpWidget(_authenticatedUploadApp());
    await tester.pumpAndSettle();
    final provider = tester
        .element(find.byType(UploadScreen))
        .read<AnalysisProvider>();
    await tester.runAsync(() async {
      final selected = Completer<void>();
      void listener() {
        if (provider.selectedFile != null && !selected.isCompleted) {
          selected.complete();
        }
      }

      provider.addListener(listener);
      try {
        await tester.tap(find.text('Tap to select an MRI scan file'));
        await selected.future.timeout(const Duration(seconds: 10));
      } finally {
        provider.removeListener(listener);
      }
    });
    await tester.pumpAndSettle();

    expect(pickerCall?.method, 'custom');
    expect(
      pickerCall?.arguments['allowedExtensions'],
      AppConstants.supportedExtensions,
    );
    expect(pickerCall?.arguments['allowMultipleSelection'], isFalse);
    expect(find.text('scan.npy'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
