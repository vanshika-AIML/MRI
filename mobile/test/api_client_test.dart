import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mri_analysis_mobile/services/api_client.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  test('401 refreshes credentials and retries once', () async {
    var attempts = 0;
    final client = ApiClient.forTesting(
      MockClient((request) async {
        if (request.url.path.endsWith('/refresh')) {
          return http.Response(
            jsonEncode({'access_token': 'new', 'refresh_token': 'rotated'}),
            200,
          );
        }
        attempts++;
        return http.Response(
          '{}',
          request.headers['Authorization'] == 'Bearer new' ? 200 : 401,
        );
      }),
    );
    await client.saveTokens(access: 'expired', refresh: 'refresh');
    expect((await client.get('/api/v1/auth/me')).statusCode, 200);
    expect(attempts, 2);
    expect(await client.getRefreshToken(), 'rotated');
  });

  test('Changing servers clears tokens and rejects invalid URLs', () async {
    final client = ApiClient.forTesting(
      MockClient((_) async => http.Response('{}', 200)),
    );
    await client.saveTokens(access: 'private', refresh: 'private-refresh');
    await client.setBaseUrl('https://example.com');
    expect(await client.getAccessToken(), isNull);
    await expectLater(
      client.setBaseUrl('file:///etc/passwd'),
      throwsFormatException,
    );
  });
}
