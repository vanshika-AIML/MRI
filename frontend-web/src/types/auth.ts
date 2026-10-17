/**
 * TypeScript types for authentication domain — Phase 9.
 */

export type UserRole = 'viewer' | 'radiologist' | 'admin';
export type UserProfession =
  | 'radiologist'
  | 'physician'
  | 'medical_student'
  | 'researcher'
  | 'viewer';

export interface UserPublicResponse {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: UserRole;
  profession: UserProfession;
  is_active: boolean;
  is_verified: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  role: UserRole;
}

export interface UserRegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  profession: UserProfession;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UserUpdateRequest {
  full_name?: string;
  current_password?: string;
  new_password?: string;
}

export interface AuthState {
  user: UserPublicResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
