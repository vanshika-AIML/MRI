import { useEffect, useState } from 'react';
import { checkBackendHealth, runMriAnalysis } from './api/analysis';
import { AuthProvider } from './contexts/AuthContext';
import { ErrorView } from './components/ErrorView';
import { FileUpload } from './components/FileUpload';
import { Header } from './components/Header';
import { LoadingView } from './components/LoadingView';
import { ResultsDashboard } from './components/ResultsDashboard';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import type { AnalysisOptions, AnalysisResponse } from './types/analysis';
import { useAuth } from './contexts/useAuth';

export function MainApp() {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(null);
  const [authView, setAuthView] = useState<'login' | 'register'>('login');

  useEffect(() => {
    if (!isAuthenticated) return;
    let isMounted = true;
    checkBackendHealth().then((connected) => {
      if (isMounted) setIsBackendConnected(connected);
    });
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated]);

  const handleFileSubmit = async (file: File, options: AnalysisOptions) => {
    setSelectedFile(file);
    setIsLoading(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const response = await runMriAnalysis(file, options);
      setAnalysisResult(response);
    } catch (err: unknown) {
      const errMsg =
        err instanceof Error ? err.message : 'An unexpected error occurred during MRI analysis.';
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setAnalysisResult(null);
    setError(null);
    setIsLoading(false);
  };

  if (isAuthLoading) {
    return (
      <main className="auth-page" aria-live="polite">
        <p role="status">Checking your sign-in…</p>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="auth-page">
        {authView === 'login' ? (
          <LoginPage onSwitchToRegister={() => setAuthView('register')} />
        ) : (
          <RegisterPage
            onSwitchToLogin={() => setAuthView('login')}
            onRegisteredSuccess={() => setAuthView('login')}
          />
        )}
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-sky-500 selection:text-white">
      <Header isBackendConnected={isBackendConnected} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading && <LoadingView filename={selectedFile?.name} />}

        {!isLoading && error && <ErrorView error={error} onReset={handleReset} />}

        {!isLoading && !error && analysisResult && (
          <ResultsDashboard response={analysisResult} file={selectedFile} onReset={handleReset} />
        )}

        {!isLoading && !error && !analysisResult && (
          <div className="space-y-8">
            <div className="text-center max-w-2xl mx-auto space-y-2">
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                MRI Research Workspace
              </h2>
              <p className="text-sm text-slate-300">
                Choose baseline heuristic processing or explicitly opt into experimental FLAIR
                whole-tumor segmentation. FLAIR sequence selection is self-declared; outputs are
                research-only and not for clinical decisions.
              </p>
            </div>

            <FileUpload onFileSubmit={handleFileSubmit} isLoading={isLoading} />
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 bg-slate-900 py-4 text-center text-xs text-slate-400">
        <p>
          MRI Analysis System • Research Use Only • Not for Clinical Decisions
        </p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
