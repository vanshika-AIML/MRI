import React, { useEffect, useState } from 'react';

interface LoadingViewProps {
  filename?: string;
}

const PIPELINE_STEPS = [
  'Parsing input scan header & pixel payload...',
  'Applying Z-score / Min-Max intensity normalization...',
  'Executing image enhancement transforms...',
  'Scanning for mathematical intensity & texture anomalies...',
  'Aggregating region coordinates & generating response...',
];

export const LoadingView: React.FC<LoadingViewProps> = ({ filename }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev < PIPELINE_STEPS.length - 1 ? prev + 1 : prev));
    }, 400);

    const timerInterval = setInterval(() => {
      setElapsedMs((prev) => prev + 50);
    }, 50);

    return () => {
      clearInterval(stepInterval);
      clearInterval(timerInterval);
    };
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto my-12 bg-slate-900/80 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center shadow-2xl relative overflow-hidden">
      {/* Glow effect */}
      <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative space-y-6">
        {/* Animated Scanner Ring */}
        <div className="relative w-24 h-24 mx-auto flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-4 border-slate-800 border-t-cyan-400 animate-spin" />
          <div className="absolute inset-2 rounded-full border-4 border-slate-800 border-b-blue-500 animate-spin animate-reverse" />
          <div className="w-12 h-12 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center text-cyan-400 font-bold text-xs">
            {(elapsedMs / 1000).toFixed(1)}s
          </div>
        </div>

        <div>
          <h3 className="text-xl font-bold text-white tracking-tight">Analyzing MRI Scan...</h3>
          {filename && <p className="text-xs text-slate-400 mt-1 font-mono">{filename}</p>}
        </div>

        {/* Step Progression Bar */}
        <div className="space-y-2 max-w-md mx-auto">
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 transition-all duration-300"
              style={{ width: `${((currentStep + 1) / PIPELINE_STEPS.length) * 100}%` }}
            />
          </div>
          <p className="text-xs text-cyan-400 font-medium animate-pulse">{PIPELINE_STEPS[currentStep]}</p>
        </div>

        <p className="text-[11px] text-slate-500 pt-2 border-t border-slate-800/80">
          NOTE: Baseline heuristic models perform mathematical signal analysis only. Duplicate submissions are disabled while processing.
        </p>
      </div>
    </div>
  );
};
