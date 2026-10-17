/// User and Authentication models matching FastAPI backend schemas.
library;

enum UserRole { viewer, radiologist, admin }

UserRole parseUserRole(String? role) {
  switch (role?.toLowerCase()) {
    case 'admin':
      return UserRole.admin;
    case 'radiologist':
      return UserRole.radiologist;
    case 'viewer':
    default:
      return UserRole.viewer;
  }
}

String userRoleToString(UserRole role) {
  switch (role) {
    case UserRole.admin:
      return 'admin';
    case UserRole.radiologist:
      return 'radiologist';
    case UserRole.viewer:
      return 'viewer';
  }
}

class UserPublic {
  final String id;
  final String email;
  final String username;
  final String? fullName;
  final UserRole role;
  final String profession;
  final bool isActive;
  final bool isVerified;

  UserPublic({
    required this.id,
    required this.email,
    required this.username,
    this.fullName,
    required this.role,
    required this.profession,
    required this.isActive,
    required this.isVerified,
  });

  factory UserPublic.fromJson(Map<String, dynamic> json) {
    return UserPublic(
      id: json['id'] as String,
      email: json['email'] as String,
      username: json['username'] as String,
      fullName: json['full_name'] as String?,
      role: parseUserRole(json['role'] as String?),
      profession: json['profession'] as String? ?? 'viewer',
      isActive: json['is_active'] as bool? ?? true,
      isVerified: json['is_verified'] as bool? ?? false,
    );
  }
}

class TokenResponse {
  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;
  final UserRole role;

  TokenResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
    required this.role,
  });

  factory TokenResponse.fromJson(Map<String, dynamic> json) {
    return TokenResponse(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      tokenType: json['token_type'] as String? ?? 'bearer',
      expiresIn: json['expires_in'] as int? ?? 1800,
      role: parseUserRole(json['role'] as String?),
    );
  }
}
