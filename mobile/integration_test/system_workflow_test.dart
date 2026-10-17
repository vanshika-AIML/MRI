import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:provider/provider.dart';
import 'package:mri_analysis_mobile/main.dart';
import 'package:mri_analysis_mobile/services/api_client.dart';
import 'package:mri_analysis_mobile/services/auth_service.dart';
import 'package:mri_analysis_mobile/providers/analysis_provider.dart';
import 'package:mri_analysis_mobile/screens/upload_screen.dart';
import 'package:mri_analysis_mobile/screens/results_screen.dart';

Uint8List _createSyntheticNiftiGzip() {
  const dimensions = [24, 20, 5];
  final voxels = dimensions.reduce((a, b) => a * b);
  final bytes = Uint8List(352 + voxels * 4);
  final header = ByteData.sublistView(bytes);
  header.setInt32(0, 348, Endian.little);
  header.setInt16(40, 3, Endian.little);
  for (var i = 0; i < dimensions.length; i++) {
    header.setInt16(42 + i * 2, dimensions[i], Endian.little);
  }
  header.setInt16(70, 16, Endian.little);
  header.setInt16(72, 32, Endian.little);
  header.setFloat32(76, 1, Endian.little);
  header.setFloat32(80, 1.5, Endian.little);
  header.setFloat32(84, 2, Endian.little);
  header.setFloat32(88, 2.5, Endian.little);
  header.setFloat32(108, 352, Endian.little);
  header.setFloat32(112, 1, Endian.little);
  header.setInt16(254, 1, Endian.little);
  final affineRows = [
    [1.5, 0.0, 0.0, 0.0],
    [0.0, 2.0, 0.0, 0.0],
    [0.0, 0.0, 2.5, 0.0],
  ];
  for (var row = 0; row < affineRows.length; row++) {
    for (var column = 0; column < affineRows[row].length; column++) {
      header.setFloat32(
        280 + row * 16 + column * 4,
        affineRows[row][column],
        Endian.little,
      );
    }
  }
  bytes.setRange(344, 348, [110, 43, 49, 0]);
  final imageData = ByteData.sublistView(bytes, 352);
  for (var i = 0; i < voxels; i++) {
    imageData.setFloat32(i * 4, (i % 101) / 100, Endian.little);
  }
  return Uint8List.fromList(GZipCodec().encode(bytes));
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'Android connects authentication, upload, inference and report UI',
    (tester) async {
      final api = ApiClient();
      await api.setBaseUrl(
        const String.fromEnvironment(
          'TEST_API_BASE_URL',
          defaultValue: 'http://10.0.2.2:8000',
        ),
      );
      final auth = AuthService();
      final suffix = DateTime.now().millisecondsSinceEpoch.toString();
      final email = 'android$suffix@example.com';
      await auth.register(
        email: email,
        username: 'android$suffix',
        password: 'SyntheticTest42!',
        profession: 'viewer',
      );
      await auth.login(email: email, password: 'SyntheticTest42!');
      expect((await auth.getCurrentUser())?.email, email);
      await tester.pumpWidget(const MriAnalysisApp());
      await tester.pumpAndSettle();
      final directory = await Directory.systemTemp.createTemp('mri-e2e');
      final file = File('${directory.path}/synthetic.png');
      await file.writeAsBytes(
        base64Decode(
          'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAAAAACPAi4CAAAAUUlEQVR4nO3VQQoAEBRF0etngRZjGRZtoIzMPmVw30jKS6cfpZFLJM9jARqggQa/vAf1tDn2qr+/QViABlD8nXEO0AANNFgJkgkL0AANuGAwAQfHAiFdjbEfAAAAAElFTkSuQmCC',
        ),
      );
      final provider = tester
          .element(find.byType(UploadScreen))
          .read<AnalysisProvider>();
      provider.setSelectedFile(file);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Run MRI Analysis'));
      await tester.pumpAndSettle(const Duration(milliseconds: 100));
      expect(
        find.byType(ResultsScreen),
        findsOneWidget,
        reason: provider.errorMessage,
      );
      expect(provider.result?.success, isTrue);
      final report = await api.get(
        '/api/v1/analysis/${provider.result!.analysisId}/report',
      );
      expect(report.statusCode, 200);
      expect(
        jsonDecode(report.body)['analysis_id'],
        provider.result!.analysisId,
      );
      await binding.convertFlutterSurfaceToImage();
      await tester.pump();
      final screenshot = await binding.takeScreenshot('results');
      await File(
        '${Directory.systemTemp.path}/mri-results.png',
      ).writeAsBytes(screenshot);
      await auth.logout();
      expect(await api.getAccessToken(), isNull);
      await directory.delete(recursive: true);
    },
  );

  testWidgets(
    'Android runs authenticated research FLAIR segmentation and retrieves report',
    (tester) async {
      final api = ApiClient();
      await api.setBaseUrl(
        const String.fromEnvironment(
          'TEST_API_BASE_URL',
          defaultValue: 'http://10.0.2.2:8000',
        ),
      );
      final auth = AuthService();
      final suffix = DateTime.now().millisecondsSinceEpoch.toString();
      final email = 'research$suffix@example.com';
      await auth.register(
        email: email,
        username: 'research$suffix',
        password: 'SyntheticTest42!',
        profession: 'researcher',
      );
      await auth.login(email: email, password: 'SyntheticTest42!');
      expect((await auth.getCurrentUser())?.email, email);

      await tester.pumpWidget(const MriAnalysisApp());
      await tester.pumpAndSettle();
      final directory = await Directory.systemTemp.createTemp('mri-flair-e2e');
      final file = File('${directory.path}/synthetic.nii.gz');
      await file.writeAsBytes(_createSyntheticNiftiGzip());
      final provider = tester
          .element(find.byType(UploadScreen))
          .read<AnalysisProvider>();
      provider.setAnalysisMethod('research_flair_segmentation');
      provider.confirmFlairSequence(true);
      provider.setSelectedFile(file);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Run MRI Analysis'));
      await tester.pump();

      final completed = await tester.runAsync(() async {
        final deadline = DateTime.now().add(const Duration(minutes: 2));
        while (provider.isLoading && DateTime.now().isBefore(deadline)) {
          await Future<void>.delayed(const Duration(milliseconds: 50));
        }
        return !provider.isLoading;
      });
      expect(completed, isTrue, reason: provider.errorMessage);
      await tester.pumpAndSettle();

      expect(find.byType(ResultsScreen), findsOneWidget);
      expect(provider.result?.success, isTrue);
      expect(provider.result?.isBaseline, isFalse);
      expect(provider.result?.prediction, isNotNull);
      final report = await api.get(
        '/api/v1/analysis/${provider.result!.analysisId}/report',
      );
      expect(report.statusCode, 200);
      final saved = jsonDecode(report.body) as Map<String, dynamic>;
      expect(saved['analysis_id'], provider.result!.analysisId);
      expect(
        (saved['prediction'] as Map<String, dynamic>)['mask_sha256'],
        provider.result!.prediction!.maskSha256,
      );

      await auth.logout();
      expect(await api.getAccessToken(), isNull);
      await directory.delete(recursive: true);
    },
  );
}
