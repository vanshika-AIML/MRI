import React from 'react';
import { useAuth } from '../contexts/useAuth';

interface HeaderProps {
  isBackendConnected?: boolean | null;
  onOpenLogin?: () => void;
  onOpenRegister?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isBackendConnected,
  onOpenLogin,
  onOpenRegister,
}) => {
  const { user, isAuthenticated, logout } = useAuth();

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      case 'radiologist':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
      case 'viewer':
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-950/95 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-sky-500/20">
            MRI
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              MRI Research Workbench
            </h1>
            <p className="text-xs text-slate-400">
              Research-only image processing • Baseline heuristics + opt-in FLAIR segmentation
            </p>
          </div>
        </div>

        {/* Right Status & Auth Bar */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 font-mono border border-slate-700">
            API v1
          </span>
          <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 font-medium">
            Research / Baseline Phase
          </span>
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-700">
            <span
              className={`w-2 h-2 rounded-full ${
                isBackendConnected === true
                  ? 'bg-emerald-500 animate-pulse'
                  : isBackendConnected === false
                  ? 'bg-rose-500'
                  : 'bg-slate-400'
              }`}
            />
            <span className="text-slate-300 font-medium">
              {isBackendConnected === true
                ? 'Backend Ready'
                : isBackendConnected === false
                ? 'Backend Offline'
                : 'Checking API...'}
            </span>
          </div>

          {/* User Auth controls */}
          <div className="flex items-center pl-2 border-l border-slate-700 gap-2">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wider border ${getRoleBadge(
                    user.role
                  )}`}
                >
                  {user.role}
                </span>
                <span className="text-[11px] text-slate-400">
                  {user.profession.replaceAll('_', ' ')}
                </span>
                <span className="font-medium text-slate-200 max-w-[120px] truncate">
                  {user.full_name || user.username}
                </span>
                <button
                  type="button"
                  onClick={() => logout()}
                  className="px-2.5 py-1 rounded-md text-slate-300 hover:text-rose-300 hover:bg-slate-800 font-medium text-xs border border-slate-700"
                  id="header-logout-btn"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onOpenLogin}
                  className="px-3 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium transition shadow-sm"
                  id="header-signin-btn"
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={onOpenRegister}
                  className="px-3 py-1 rounded-lg text-slate-200 bg-slate-800 hover:bg-slate-700 font-medium border border-slate-700"
                  id="header-register-btn"
                >
                  Register
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
