/**
 * Authentication context — Phase 9.
 * Provides user state, login, logout, and register actions app-wide.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { AuthContext } from './useAuth';
import type { AuthState } from '../types/auth';
import {
  loginUser,
  logoutUser,
  registerUser,
  getCurrentUser,
  expireSession,
  isLoggedIn,
} from '../api/auth';
import type { UserLoginRequest, UserRegisterRequest } from '../types/auth';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: isLoggedIn(),
    error: null,
  });

  const setError = (error: string | null) =>
    setState((s) => ({ ...s, error, isLoading: false }));

  const clearError = useCallback(() => setError(null), []);

  // Restore session from stored token on mount
  useEffect(() => {
    const onSessionExpired = () => {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: 'Your session has expired. Please sign in again.',
      });
    };
    window.addEventListener('mri:session-expired', onSessionExpired);
    if (!isLoggedIn()) {
      return () => window.removeEventListener('mri:session-expired', onSessionExpired);
    }
    getCurrentUser()
      .then((user) =>
        setState({ user, isAuthenticated: true, isLoading: false, error: null })
      )
      .catch(() => {
        expireSession();
      });
    return () => window.removeEventListener('mri:session-expired', onSessionExpired);
  }, []);

  const login = useCallback(async (data: UserLoginRequest) => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      await loginUser(data);
      const user = await getCurrentUser();
      setState({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed.';
      setError(msg);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true }));
    await logoutUser();
    setState({ user: null, isAuthenticated: false, isLoading: false, error: null });
  }, []);

  const register = useCallback(async (data: UserRegisterRequest) => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const user = await registerUser(data);
      setState((s) => ({ ...s, isLoading: false, error: null }));
      return user;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Registration failed.';
      setError(msg);
      throw err;
    }
  }, []);

  const refreshUser = useCallback(async () => {
    if (!isLoggedIn()) return;
    try {
      const user = await getCurrentUser();
      setState((s) => ({ ...s, user }));
    } catch {
      expireSession();
    }
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, register, clearError, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}
