/**
 * LoginPage — Phase 9 Auth UI.
 * Clean clinical light-theme login form with real-time validation feedback.
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/useAuth';

interface LoginPageProps {
  onSuccess?: () => void;
  onSwitchToRegister: () => void;
}

export default function LoginPage({ onSwitchToRegister, onSuccess }: LoginPageProps) {
  const { login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();
    if (!email.trim() || !password) {
      setLocalError('Email and password are required.');
      return;
    }
    try {
      await login({ email: email.trim(), password });
      onSuccess?.();
    } catch {
      // Error is set in context
    }
  };

  const displayError = localError || error;

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Header */}
        <div className="auth-card__header">
          <div className="auth-card__logo">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <rect width="32" height="32" rx="8" fill="#0ea5e9"/>
              <path d="M8 16h4l3-7 4 14 3-9 2 2h4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h1 className="auth-card__title">MRI Analysis</h1>
          <p className="auth-card__subtitle">Sign in to the research-only MRI workspace</p>
        </div>

        {/* Error banner */}
        {displayError && (
          <div className="auth-error" role="alert">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="#dc2626" strokeWidth="1.5"/>
              <path d="M8 5v4M8 11v.5" stroke="#dc2626" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <span>{displayError}</span>
          </div>
        )}

        {/* Form */}
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="auth-field">
            <label className="auth-label" htmlFor="login-email">
              Email address
            </label>
            <input
              id="login-email"
              type="email"
              className="auth-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
              disabled={isLoading}
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="login-password">
              Password
            </label>
            <div className="auth-password-input">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="current-password"
                required
                disabled={isLoading}
              />
              <button
                type="button"
                className="auth-password-toggle"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setShowPassword((visible) => !visible)}
                disabled={isLoading}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <button
            id="login-submit-btn"
            type="submit"
            className="auth-btn auth-btn--primary"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="auth-btn__spinner" aria-label="Signing in…" />
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Footer */}
        <p className="auth-card__footer">
          Don&apos;t have an account?{' '}
          <button
            id="switch-to-register-btn"
            type="button"
            className="auth-link"
            onClick={onSwitchToRegister}
            disabled={isLoading}
          >
            Create account
          </button>
        </p>

        {/* Clinical disclaimer */}
        <p className="auth-card__disclaimer">
          Research use only. Profession is self-reported and does not verify qualifications.
        </p>
      </div>
    </div>
  );
}
