import React from 'react';

interface ErrorViewProps {
  error: string;
  onReset: () => void;
}

export const ErrorView: React.FC<ErrorViewProps> = ({ error, onReset }) => {
  return (
    <div className="w-full max-w-xl mx-auto my-8 bg-rose-950/20 border border-rose-500/30 rounded-2xl p-8 text-center space-y-6 shadow-2xl">
      <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center">
        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>

      <div className="space-y-2">
        <h3 className="text-lg font-bold text-white tracking-tight">Analysis Request Failed</h3>
        <p className="text-xs text-rose-300 max-w-md mx-auto">{error}</p>
      </div>

      <div className="pt-2">
        <button
          type="button"
          onClick={onReset}
          className="px-6 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs border border-slate-700 transition"
        >
          Try Again / Select Different File
        </button>
      </div>
    </div>
  );
};
