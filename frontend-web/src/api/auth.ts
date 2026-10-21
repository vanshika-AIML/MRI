/**
 * Authentication API client — Phase 9
 * Manages login, registration, token refresh, and profile operations.
 */

import type {
  TokenResponse,
  UserPublicResponse,
  UserRegisterRequest,
  UserLoginRequest,
  UserUpdateRequest,
} from '../types/auth';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000'
    : 'http://127.0.0.1:8000');

// ---------------------------------------------------------------------------
// Token storage (in-memory + sessionStorage for page refresh resilience)
// ---------------------------------------------------------------------------

const TOKEN_KEY = 'mri_access_token';
const REFRESH_KEY = 'mri_refresh_token';

export function storeTokens(tokens: TokenResponse): void {
  sessionStorage.setItem(TOKEN_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

export function expireSession(): void {
  clearTokens();
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('mri:session-expired'));
  }
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  withAuth = false,
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (withAuth) {
    const token = getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    signal: AbortSignal.timeout(20000),
  });

  if (response.status === 401 && withAuth) {
    if (retry && getRefreshToken()) {
      try {
        await refreshTokens();
        return apiFetch<T>(path, options, withAuth, false);
      } catch (error) {
        expireSession();
        throw error;
      }
    }
    expireSession();
    throw new Error('Your session has expired. Please sign in again.');
  }

  if (!response.ok) {
    let message = `Server error (${response.status})`;
    try {
      const err = await response.json();
      message = err?.error?.message || err?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

/** Shared authenticated JSON requests, including the existing single-flight refresh. */
export function authenticatedJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  return apiFetch<T>(path, options, true);
}

// ---------------------------------------------------------------------------
// Auth API calls
// ---------------------------------------------------------------------------

export async function registerUser(data: UserRegisterRequest): Promise<UserPublicResponse> {
  return apiFetch<UserPublicResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function loginUser(data: UserLoginRequest): Promise<TokenResponse> {
  const tokens = await apiFetch<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  storeTokens(tokens);
  return tokens;
}

export async function logoutUser(): Promise<void> {
  try {
    await apiFetch<unknown>('/api/v1/auth/logout', { method: 'POST' }, true);
  } catch {
    // Best-effort — always clear local tokens
  } finally {
    clearTokens();
  }
}

export async function getCurrentUser(): Promise<UserPublicResponse> {
  return apiFetch<UserPublicResponse>('/api/v1/auth/me', { method: 'GET' }, true);
}

export async function updateProfile(data: UserUpdateRequest): Promise<UserPublicResponse> {
  return apiFetch<UserPublicResponse>(
    '/api/v1/auth/me',
    { method: 'PATCH', body: JSON.stringify(data) },
    true,
  );
}

let refreshInFlight: Promise<TokenResponse> | null = null;
export async function refreshTokens(): Promise<TokenResponse> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const refresh_token = getRefreshToken();
    if (!refresh_token) throw new Error('No refresh token available.');
    const tokens = await apiFetch<TokenResponse>('/api/v1/auth/refresh', {
      method: 'POST', body: JSON.stringify({ refresh_token }),
    });
    storeTokens(tokens);
    return tokens;
  })();
  try { return await refreshInFlight; } finally { refreshInFlight = null; }
}

/** Check whether a stored access token exists (heuristic — not a server round-trip). */
export function isLoggedIn(): boolean {
  return !!getAccessToken();
}
