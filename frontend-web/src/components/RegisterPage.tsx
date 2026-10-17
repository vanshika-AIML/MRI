/**
 * RegisterPage — Phase 9 Auth UI.
 * Clean clinical light-theme registration form with real-time validation feedback.
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/useAuth';

interface RegisterPageProps {
  onSwitchToLogin: () => void;
  onRegisteredSuccess?: () => void;
}

export default function RegisterPage({ onSwitchToLogin, onRegisteredSuccess }: RegisterPageProps) {
  const { register, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [profession, setProfession] = useState<'radiologist' | 'physician' | 'medical_student' | 'researcher' | 'viewer'>('viewer');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !username.trim() || !password) {
      setLocalError('Email, username, and password are required.');
      return;
    }
    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters long.');
      return;
    }
    if (!/\d/.test(password)) {
      setLocalError('Password must contain at least one numeric digit.');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    try {
      await register({
        email: email.trim(),
        username: username.trim(),
        password,
        full_name: fullName.trim() || undefined,
        profession,
      });
      setSuccessMessage('Registration successful! You can now sign in.');
      if (onRegisteredSuccess) {
        onRegisteredSuccess();
      }
    } catch {
      // Error handled in AuthContext
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
              <rect width="32" height="32" rx="8" fill="#0ea5e9" />
              <path
                d="M8 16h4l3-7 4 14 3-9 2 2h4"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h1 className="auth-card__title">Create Account</h1>
          <p className="auth-card__subtitle">Create an account for research-only MRI tools</p>
        </div>

        {/* Success banner */}
        {successMessage && (
          <div className="auth-success" role="status">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M3 8.5L6.5 12L13 4"
                stroke="#16a34a"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>{successMessage}</span>
          </div>
        )}

        {/* Error banner */}
        {displayError && (
          <div className="auth-error" role="alert">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="#dc2626" strokeWidth="1.5" />
              <path d="M8 5v4M8 11v.5" stroke="#dc2626" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span>{displayError}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="auth-field">
            <label htmlFor="reg-email" className="auth-label">
              Email Address <span className="auth-required">*</span>
            </label>
            <input
              id="reg-email"
              type="email"
              className="auth-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="clinician@hospital.org"
              autoComplete="email"
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="reg-username" className="auth-label">
              Username <span className="auth-required">*</span>
            </label>
            <input
              id="reg-username"
              type="text"
              className="auth-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="dr_smith"
              autoComplete="username"
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="reg-fullname" className="auth-label">
              Full Name
            </label>
            <input
              id="reg-fullname"
              type="text"
              className="auth-input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Dr. Jane Smith, MD"
              autoComplete="name"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="reg-profession" className="auth-label">
              Profession <span className="auth-required">*</span>
            </label>
            <select
              id="reg-profession"
              className="auth-input"
              value={profession}
              onChange={(e) => setProfession(e.target.value as typeof profession)}
              required
            >
              <option value="radiologist">Radiologist</option>
              <option value="physician">Doctor / physician</option>
              <option value="medical_student">Medical student</option>
              <option value="researcher">Researcher</option>
              <option value="viewer">Other / viewer</option>
            </select>
            <p className="auth-hint">Self-reported only; this does not verify credentials or grant access.</p>
          </div>

          <div className="auth-field">
            <label htmlFor="reg-password" className="auth-label">
              Password <span className="auth-required">*</span>
            </label>
            <div className="auth-password-input">
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 8 chars with 1+ digit"
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                className="auth-password-toggle"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <p className="auth-hint">Must be at least 8 characters and contain at least one digit.</p>
          </div>

          <div className="auth-field">
            <label htmlFor="reg-confirm-password" className="auth-label">
              Confirm Password <span className="auth-required">*</span>
            </label>
            <div className="auth-password-input">
              <input
                id="reg-confirm-password"
                type={showConfirmPassword ? 'text' : 'password'}
                className="auth-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                className="auth-password-toggle"
                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setShowConfirmPassword((visible) => !visible)}
              >
                {showConfirmPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="auth-btn auth-btn--primary"
            disabled={isLoading}
            id="register-submit-btn"
          >
            {isLoading ? (
              <span className="auth-btn__loading">
                <span className="auth-spinner" />
                Creating Account...
              </span>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        {/* Footer switch */}
        <div className="auth-card__footer">
          <span>Already have an account? </span>
          <button
            type="button"
            className="auth-link"
            onClick={onSwitchToLogin}
            id="switch-to-login-btn"
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
}
