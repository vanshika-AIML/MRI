import { useState } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { useAuth } from './contexts/useAuth';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import { Workspace } from './components/Workspace';

function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="auth-layout">
      <aside className="auth-brand-panel">
        <a className="auth-brand" href="#/" aria-label="MRI AI research workspace">
          <span className="auth-brand-mark" aria-hidden="true">M</span>
          MRI AI SYSTEM
        </a>
        <div className="auth-brand-copy">
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Review every scan with clarity.</h1>
          <p>Secure access to experimental MRI image processing and research segmentation workflows.</p>
          <ul className="auth-capabilities">
            <li>Account-owned analysis history</li>
            <li>Original model output retained</li>
            <li>Role-authorized review notes</li>
            <li>Explicit research limitations</li>
          </ul>
        </div>
        <div className="auth-brand-footer">
          <strong>Research use only</strong>
          Outputs are experimental and do not constitute a diagnosis or medical advice.
        </div>
      </aside>
      {children}
    </main>
  );
}

export function MainApp() {
  const { isAuthenticated, isLoading } = useAuth();
  const [authView, setAuthView] = useState<'login' | 'register'>('login');
  if (isLoading) {
    return (
      <AuthShell>
        <div className="auth-page"><p className="inline-loading" role="status">Checking your sign-in…</p></div>
      </AuthShell>
    );
  }
  if (!isAuthenticated) return (
    <AuthShell>
      {authView === 'login'
        ? <LoginPage onSwitchToRegister={() => setAuthView('register')} />
        : <RegisterPage onSwitchToLogin={() => setAuthView('login')} onRegisteredSuccess={() => setAuthView('login')} />}
    </AuthShell>
  );
  return <Workspace />;
}

export default function App() {
  return <AuthProvider><MainApp /></AuthProvider>;
}
