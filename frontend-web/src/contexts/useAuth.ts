import { createContext, useContext } from 'react';
import type { AuthState, UserPublicResponse, UserLoginRequest, UserRegisterRequest } from '../types/auth';
interface AuthContextValue extends AuthState {
  login: (data: UserLoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: UserRegisterRequest) => Promise<UserPublicResponse>;
  clearError: () => void;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
