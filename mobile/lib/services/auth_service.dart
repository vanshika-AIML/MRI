import 'dart:convert';
import '../core/constants.dart';
import '../models/user.dart';
import 'api_client.dart';

/// Authentication Service connecting to FastAPI auth endpoints.
class AuthService {
  final ApiClient _client = ApiClient();

  Future<TokenResponse> login({
    required String email,
    required String password,
  }) async {
    final response = await _client.post(
      AppConstants.authLoginPath,
      body: {'email': email.trim(), 'password': password},
      auth: false,
    );

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final tokenResp = TokenResponse.fromJson(json);
      await _client.saveTokens(
        access: tokenResp.accessToken,
        refresh: tokenResp.refreshToken,
      );
      return tokenResp;
    } else {
      final errorMsg = _extractErrorMessage(response.body, response.statusCode);
      throw Exception(errorMsg);
    }
  }

  Future<UserPublic> register({
    required String email,
    required String username,
    required String password,
    required String profession,
    String? fullName,
  }) async {
    final body = <String, dynamic>{
      'email': email.trim(),
      'username': username.trim(),
      'password': password,
      'profession': profession,
    };
    if (fullName != null && fullName.trim().isNotEmpty) {
      body['full_name'] = fullName.trim();
    }

    final response = await _client.post(
      AppConstants.authRegisterPath,
      body: body,
      auth: false,
    );

    if (response.statusCode == 201) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return UserPublic.fromJson(json);
    } else {
      final errorMsg = _extractErrorMessage(response.body, response.statusCode);
      throw Exception(errorMsg);
    }
  }

  Future<UserPublic?> getCurrentUser() async {
    final token = await _client.getAccessToken();
    if (token == null || token.isEmpty) return null;

    final response = await _client.get(AppConstants.authMePath, auth: true);
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return UserPublic.fromJson(json);
    } else if (response.statusCode == 401) {
      await _client.clearTokens();
      return null;
    } else {
      return null;
    }
  }

  Future<void> logout() async {
    try {
      await _client.post(AppConstants.authLogoutPath, auth: true);
    } catch (_) {
      // Ignore network errors during logout
    } finally {
      await _client.clearTokens();
    }
  }

  String _extractErrorMessage(String body, int statusCode) {
    try {
      final json = jsonDecode(body);
      if (json is Map && json['error'] is Map) {
        return json['error']['message'].toString();
      }
      if (json is Map && json['detail'] != null) {
        final d = json['detail'];
        if (d is String) return d;
        if (d is List && d.isNotEmpty && d[0]['msg'] != null) {
          return d[0]['msg'].toString();
        }
      }
    } catch (_) {}
    return 'Authentication error (HTTP $statusCode)';
  }
}
