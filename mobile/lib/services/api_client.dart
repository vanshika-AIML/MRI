import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import '../core/constants.dart';

/// Base HTTP client providing authentication headers,
/// secure token storage, and consistent error handling.
class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();
  ApiClient.forTesting(http.Client client) : _http = client;
  http.Client _http = http.Client();
  Future<bool>? _refreshing;

  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String _baseUrl = Platform.isAndroid
      ? AppConstants.defaultBaseUrl
      : AppConstants.defaultIosBaseUrl;

  String get baseUrl => _baseUrl;

  Future<void> setBaseUrl(String url) async {
    final uri = Uri.tryParse(url.trim());
    if (uri == null ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        !['http', 'https'].contains(uri.scheme) ||
        (!kDebugMode && uri.scheme != 'https')) {
      throw const FormatException(
        'Enter a valid HTTPS server URL (HTTP is allowed in debug builds).',
      );
    }
    final normalized = url.trim().replaceFirst(RegExp(r'/$'), '');
    if (normalized != _baseUrl) {
      await clearTokens();
      _baseUrl = normalized;
    }
  }

  static const String _accessTokenKey = 'mri_access_token';
  static const String _refreshTokenKey = 'mri_refresh_token';

  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    await _storage.write(key: _accessTokenKey, value: access);
    await _storage.write(key: _refreshTokenKey, value: refresh);
  }

  Future<String?> getAccessToken() async {
    return await _storage.read(key: _accessTokenKey);
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }

  Future<Map<String, String>> _buildHeaders({bool includeAuth = true}) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (includeAuth) {
      final token = await getAccessToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  Future<http.Response> get(String path, {bool auth = true}) async {
    final uri = Uri.parse('$_baseUrl$path');
    final headers = await _buildHeaders(includeAuth: auth);
    return _authorized(
      () =>
          _http.get(uri, headers: headers).timeout(const Duration(seconds: 20)),
      headers,
      auth,
    );
  }

  Future<http.Response> post(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) async {
    final uri = Uri.parse('$_baseUrl$path');
    final headers = await _buildHeaders(includeAuth: auth);
    return _authorized(
      () => _http
          .post(
            uri,
            headers: headers,
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(const Duration(seconds: 20)),
      headers,
      auth,
    );
  }

  Future<http.Response> patch(
    String path, {
    Map<String, dynamic>? body,
    bool auth = true,
  }) async {
    final uri = Uri.parse('$_baseUrl$path');
    final headers = await _buildHeaders(includeAuth: auth);
    return _authorized(
      () => _http
          .patch(
            uri,
            headers: headers,
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(const Duration(seconds: 20)),
      headers,
      auth,
    );
  }

  Future<http.Response> _authorized(
    Future<http.Response> Function() send,
    Map<String, String> headers,
    bool auth,
  ) async {
    var response = await send();
    if (auth && response.statusCode == 401 && await refreshTokens()) {
      headers['Authorization'] = 'Bearer ${await getAccessToken()}';
      response = await send();
    }
    return response;
  }

  Future<bool> refreshTokens() async {
    if (_refreshing != null) return _refreshing!;
    _refreshing = _refresh();
    try {
      return await _refreshing!;
    } finally {
      _refreshing = null;
    }
  }

  Future<bool> _refresh() async {
    final token = await getRefreshToken();
    if (token == null) return false;
    final response = await _http
        .post(
          Uri.parse('$_baseUrl${AppConstants.authRefreshPath}'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh_token': token}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await saveTokens(
        access: data['access_token'] as String,
        refresh: data['refresh_token'] as String,
      );
      return true;
    }
    if (response.statusCode == 401) await clearTokens();
    return false;
  }
}
