import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  checkBackendHealth,
  getOwnedReport,
  listOwnedReports,
  runMriAnalysis,
  type ReportSummary,
} from '../api/analysis';
import { authenticatedJson, updateProfile } from '../api/auth';
import { useAuth } from '../contexts/useAuth';
import type { AnalysisOptions, AnalysisResponse } from '../types/analysis';
import type { UserPublicResponse, UserRole } from '../types/auth';
import { FileUpload } from './FileUpload';
import { LoadingView } from './LoadingView';
import { ResultsDashboard } from './ResultsDashboard';

type Page = 'dashboard' | 'cases' | 'patients' | 'viewer' | 'reports' | 'settings' | 'admin';
type IconName = 'dashboard' | 'cases' | 'patients' | 'viewer' | 'reports' | 'settings' | 'admin';

const pages: Page[] = ['dashboard', 'cases', 'patients', 'viewer', 'reports', 'settings', 'admin'];
const labels: Record<Page, string> = {
  dashboard: 'Dashboard',
  cases: 'Cases',
  patients: 'Patients',
  viewer: 'MRI Viewer',
  reports: 'Reports',
  settings: 'Settings',
  admin: 'Admin Panel',
};
const icons: Record<IconName, string> = {
  dashboard: 'M3 3h8v8H3z M13 3h8v5h-8z M13 10h8v11h-8z M3 13h8v8H3z',
  cases: 'M4 4h16v16H4z M8 8h8 M8 12h8 M8 16h5',
  patients: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0',
  viewer: 'M3 4h18v16H3z M8 4v16 M16 4v16',
  reports: 'M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h7',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M19 13a7 7 0 0 0 0-2l2-1-2-4-2 1a7 7 0 0 0-2-1l-.4-2h-5L9 6a7 7 0 0 0-2 1L5 6l-2 4 2 1a7 7 0 0 0 0 2l-2 1 2 4 2-1a7 7 0 0 0 2 1l.4 2h5L15 18a7 7 0 0 0 2-1l2 1 2-4z',
  admin: 'M12 3 20 6v5c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6z M9 12l2 2 4-4',
};

function route(): Page {
  const candidate = window.location.hash.replace(/^#\/?/, '').split('/')[0];
  return pages.includes(candidate as Page) ? (candidate as Page) : 'dashboard';
}

function navigateTo(page: Page) {
  window.location.hash = `#/${page}`;
}

function displayDate(value: string) {
  return Number.isNaN(Date.parse(value)) ? 'Unknown date' : new Date(value).toLocaleString();
}

function EmptyState({ title, children }: { title: string; children: string }) {
  return (
    <div className="empty-state">
      <span className="empty-state-mark" aria-hidden="true">—</span>
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}

export function Workspace() {
  const { user, logout, refreshUser } = useAuth();
  const [page, setPage] = useState<Page>(() => {
    const requested = route();
    return requested === 'admin' && user?.role !== 'admin' ? 'dashboard' : requested;
  });
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [reportsError, setReportsError] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [caseTab, setCaseTab] = useState<'pending' | 'review' | 'completed'>('completed');
  const [reportTab, setReportTab] = useState<'draft' | 'edit' | 'final'>('draft');
  const [patientTab, setPatientTab] = useState<'overview' | 'studies' | 'history'>('overview');
  const [name, setName] = useState(user?.full_name || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [targetUser, setTargetUser] = useState('');
  const [targetRole, setTargetRole] = useState<UserRole>('viewer');
  const [adminMessage, setAdminMessage] = useState<string | null>(null);

  const reloadReports = useCallback(async () => {
    try {
      setReports(await listOwnedReports());
      setReportsError(null);
    } catch (reason) {
      setReportsError(reason instanceof Error ? reason.message : 'Could not load reports.');
    } finally {
      setReportsLoading(false);
    }
  }, []);

  const refreshReports = useCallback(() => {
    setReportsLoading(true);
    return reloadReports();
  }, [reloadReports]);

  useEffect(() => {
    const onHash = () => {
      const requested = route();
      setPage(requested === 'admin' && user?.role !== 'admin' ? 'dashboard' : requested);
    };
    window.addEventListener('hashchange', onHash);
    void Promise.resolve().then(reloadReports);
    void checkBackendHealth().then(setConnected);
    return () => window.removeEventListener('hashchange', onHash);
  }, [reloadReports, user?.role]);

  const filteredReports = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return reports;
    return reports.filter((item) =>
      `${item.filename} ${item.analysis_id} ${item.model_name} ${item.patient_id || ''}`
        .toLowerCase()
        .includes(query),
    );
  }, [reports, search]);

  const openReport = async (id: string) => {
    setError(null);
    setWorking(true);
    try {
      setResult(await getOwnedReport(id));
      setFile(null);
      navigateTo('reports');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not open report.');
    } finally {
      setWorking(false);
    }
  };

  const analyze = async (selected: File, options: AnalysisOptions) => {
    setFile(selected);
    setResult(null);
    setError(null);
    setWorking(true);
    try {
      const next = await runMriAnalysis(selected, options);
      if (!next.success || next.status === 'failed') {
        throw new Error(next.error_message || 'We could not analyze this scan.');
      }
      setResult(next);
      await refreshReports();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'We could not analyze this scan.');
    } finally {
      setWorking(false);
    }
  };

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    setProfileMessage(null);
    try {
      await updateProfile({
        full_name: name.trim(),
        ...(newPassword
          ? { current_password: currentPassword, new_password: newPassword }
          : {}),
      });
      await refreshUser();
      setCurrentPassword('');
      setNewPassword('');
      setProfileMessage('Profile saved.');
    } catch (reason) {
      setProfileMessage(reason instanceof Error ? reason.message : 'Could not save profile.');
    }
  };

  const changeRole = async (event: FormEvent) => {
    event.preventDefault();
    setAdminMessage(null);
    try {
      const changed = await authenticatedJson<UserPublicResponse>(
        `/api/v1/auth/users/${encodeURIComponent(targetUser.trim())}/role?role=${targetRole}`,
        { method: 'PUT' },
      );
      setAdminMessage(`${changed.username} is now ${changed.role}.`);
    } catch (reason) {
      setAdminMessage(reason instanceof Error ? reason.message : 'Role update failed.');
    }
  };

  const linkedReports = useMemo(
    () => filteredReports.filter((item) => item.patient_id),
    [filteredReports],
  );
  const linkedPatients = useMemo(() => {
    const patients = new Map<string, ReportSummary[]>();
    for (const report of linkedReports) {
      const id = report.patient_id;
      if (!id) continue;
      patients.set(id, [...(patients.get(id) || []), report]);
    }
    return [...patients.entries()];
  }, [linkedReports]);

  const listReports = (items: ReportSummary[], emptyTitle = 'No saved analyses') => items.length ? (
    <div className="record-list">
      {items.map((item) => (
        <button
          className="record-row"
          type="button"
          key={item.analysis_id}
          onClick={() => void openReport(item.analysis_id)}
          aria-label={`Open ${item.filename}, ${item.success ? 'analysis saved' : 'analysis failed'}`}
        >
          <span className="record-icon" aria-hidden="true">MR</span>
          <span className="record-main">
            <strong>{item.filename}</strong>
            <small>{item.model_name.replaceAll('_', ' ')} · {displayDate(item.timestamp)}</small>
          </span>
          <span className={`record-status ${item.success ? 'status-complete' : 'status-failed'}`}>
            {item.success ? 'Analysis saved' : 'Analysis failed'}
          </span>
          <span className="record-open" aria-hidden="true">↗</span>
        </button>
      ))}
    </div>
  ) : (
    <EmptyState title={emptyTitle}>
      Analyze a scan to create an account-owned research report.
    </EmptyState>
  );

  const showPatientView = () => {
    if (reportsLoading) return <p className="inline-loading" role="status">Loading linked studies…</p>;
    if (!linkedPatients.length) {
      return (
        <EmptyState title="No linked patients">
          Saved analyses do not include patient identifiers. This workspace is not connected to a patient registry.
        </EmptyState>
      );
    }
    if (patientTab === 'overview') {
      return (
        <div className="patient-grid">
          {linkedPatients.map(([patientId, studies]) => (
            <article className="patient-card" key={patientId}>
              <span className="patient-avatar" aria-hidden="true">ID</span>
              <div><small>Source identifier</small><strong>{patientId}</strong></div>
              <span className="patient-study-count">{studies.length} {studies.length === 1 ? 'study' : 'studies'}</span>
            </article>
          ))}
        </div>
      );
    }
    if (patientTab === 'studies') return listReports(linkedReports);
    return (
      <ol className="history-list">
        {linkedReports.map((report) => (
          <li key={report.analysis_id}>
            <time>{displayDate(report.timestamp)}</time>
            <strong>{report.patient_id}</strong>
            <span>{report.filename} · {report.success ? 'Analysis saved' : 'Analysis failed'}</span>
            <button type="button" onClick={() => void openReport(report.analysis_id)}>Open report</button>
          </li>
        ))}
      </ol>
    );
  };

  const adminPage = user?.role === 'admin' && (
    <section className="surface narrow">
      <div className="section-head">
        <div><h2>Role management</h2><p>Change the authorization role for a known account ID.</p></div>
      </div>
      <div className="notice notice-info">
        The API enforces administrator permissions. A browsable user directory and audit-log endpoint are not available.
      </div>
      <form className="settings-form" onSubmit={(event) => void changeRole(event)}>
        <label>User ID<input value={targetUser} onChange={(event) => setTargetUser(event.target.value)} required /></label>
        <label>Authorization role
          <select value={targetRole} onChange={(event) => setTargetRole(event.target.value as UserRole)}>
            <option value="viewer">Viewer</option>
            <option value="radiologist">Radiologist</option>
            <option value="admin">Administrator</option>
          </select>
        </label>
        <button className="primary-link" type="submit" disabled={!targetUser.trim()}>Update role</button>
      </form>
      {adminMessage && <p className="inline-message" role="status">{adminMessage}</p>}
    </section>
  );

  return (
    <div className={`workspace-shell ${page === 'viewer' ? 'is-viewer' : ''}`}>
      <aside className="workspace-sidebar" aria-label="Workspace navigation">
        <a className="brand" href="#/dashboard">
          <span className="brand-mark" aria-hidden="true">M</span>
          <span><strong>MRI AI SYSTEM</strong><small>Research workspace</small></span>
        </a>
        <div className="nav-group-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {pages.filter((item) => item !== 'admin' || user?.role === 'admin').map((item) => (
            <a
              key={item}
              href={`#/${item}`}
              aria-current={page === item ? 'page' : undefined}
              className={`nav-item ${page === item ? 'active' : ''}`}
            >
              <svg className="nav-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d={icons[item]} />
              </svg>
              {labels[item]}
            </a>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-note">
          <span className="status-dot" /> RESEARCH ENVIRONMENT
          <p>Outputs are experimental and do not provide a diagnosis.</p>
        </div>
        <div className="sidebar-user">
          <span className="user-avatar">{(user?.full_name || user?.username || 'U').slice(0, 1).toUpperCase()}</span>
          <span><strong>{user?.full_name || user?.username}</strong><small>{user?.profession.replaceAll('_', ' ')} · {user?.role}</small></span>
        </div>
      </aside>

      <div className="workspace-column">
        <header className="workspace-topbar">
          <a className="mobile-brand" href="#/dashboard">MRI AI SYSTEM</a>
          <div className="breadcrumbs">Workspace <span>/</span> <strong>{labels[page]}</strong></div>
          <div className="topbar-actions">
            <form className="global-search" role="search" onSubmit={(event) => { event.preventDefault(); navigateTo('cases'); }}>
              <label className="sr-only" htmlFor="workspace-search">Search reports and cases</label>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.5 4.5" /></svg>
              <input id="workspace-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search workspace" />
            </form>
            <span className={`connection ${connected === true ? 'online' : connected === false ? 'offline' : ''}`} role="status">
              <i />{connected === true ? 'API connected' : connected === false ? 'API unavailable' : 'Checking API'}
            </span>
            <button type="button" onClick={() => void logout()}>Sign out</button>
          </div>
        </header>

        <main className="workspace-main" id="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">MRI AI / {labels[page]}</p>
              <h1>{labels[page]}</h1>
              <p>{page === 'dashboard'
                ? 'Review recent work and start a research analysis.'
                : page === 'viewer'
                  ? 'Inspect source imagery and experimental output.'
                  : page === 'reports'
                    ? 'Review account-owned analysis reports and annotations.'
                    : page === 'cases'
                      ? 'Search saved analyses; workflow queues are not available.'
                      : page === 'patients'
                        ? 'Explore identifiers linked to your saved analyses.'
                        : page === 'settings'
                          ? 'Manage your profile and sign-in credentials.'
                          : 'Manage account roles with administrator authorization.'}</p>
            </div>
            {page !== 'viewer' && page !== 'dashboard' && (
              <a className="primary-link" href="#/viewer"><span aria-hidden="true">＋</span> Analyze scan</a>
            )}
          </div>

          {error && <div className="notice error" role="alert">{error}<button type="button" onClick={() => setError(null)} aria-label="Dismiss error">×</button></div>}
          {reportsError && (
            <div className="notice error" role="alert">
              Reports unavailable: {reportsError}
              <button type="button" onClick={() => void refreshReports()}>Retry</button>
            </div>
          )}

          {page === 'dashboard' && (
            <>
              <div className="metric-grid">
                <div className="metric"><small>Saved analyses</small><strong>{reportsLoading ? '—' : reports.length}</strong><span>Owned by your account</span></div>
                <div className="metric"><small>Research masks</small><strong>{reportsLoading ? '—' : reports.filter((item) => item.has_prediction).length}</strong><span>Experimental segmentations</span></div>
                <div className="metric"><small>Analysis failures</small><strong>{reportsLoading ? '—' : reports.filter((item) => !item.success).length}</strong><span>Saved API outcomes</span></div>
              </div>
              <div className="dashboard-grid">
                <section className="surface">
                  <div className="section-head">
                    <div><h2>Recent analyses</h2><p>Latest reports saved to your account</p></div>
                    <a href="#/cases">View cases <span aria-hidden="true">→</span></a>
                  </div>
                  {reportsLoading
                    ? <p className="inline-loading" role="status">Loading saved analyses…</p>
                    : reportsError
                      ? <EmptyState title="Recent analyses unavailable">Retry the report request above to check the service.</EmptyState>
                      : listReports(filteredReports.slice(0, 5))}
                </section>
                <section className="surface workflow-card">
                  <p className="eyebrow">RESEARCH WORKFLOW</p>
                  <h2>From scan to review</h2>
                  <p>Available processing stages depend on the uploaded file and selected method. Model output is not a final clinical diagnosis.</p>
                  <ol className="workflow-steps">
                    <li><span>01</span>Upload a supported scan</li>
                    <li><span>02</span>Run a selected analysis method</li>
                    <li><span>03</span>Review the original output</li>
                    <li><span>04</span>Add a role-authorized note</li>
                  </ol>
                  <p className="workflow-limit">Final diagnosis and clinical sign-off happen outside this research workspace.</p>
                  <a className="primary-link" href="#/viewer">Open MRI Viewer <span aria-hidden="true">→</span></a>
                </section>
              </div>
            </>
          )}

          {page === 'cases' && (
            <section className="surface">
              <div className="section-head section-head-wrap">
                <div><h2>Saved analysis cases</h2><p>Only reports accessible to the signed-in account are listed.</p></div>
                <label className="search-box">
                  <span className="sr-only">Search filename or ID</span>
                  <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search filename or ID" />
                </label>
              </div>
              <div className="tabs" role="tablist" aria-label="Case status">
                {([['pending', 'Pending'], ['review', 'In review'], ['completed', 'Completed']] as const).map(([key, label]) => (
                  <button type="button" role="tab" aria-selected={caseTab === key} onClick={() => setCaseTab(key)} key={key}>{label}</button>
                ))}
              </div>
              {caseTab === 'completed'
                ? reportsLoading
                  ? <p className="inline-loading" role="status">Loading cases…</p>
                  : listReports(filteredReports.filter((item) => item.success && item.status === 'completed'), 'No completed analyses')
                : caseTab === 'pending'
                  ? <EmptyState title="No pending queue is available">The API exposes saved analysis history only; it does not provide an upload queue or case-assignment state.</EmptyState>
                  : <EmptyState title="No review queue is available">The API does not expose reviewer assignments or review-transition status. Open a saved report to add an authorized review note.</EmptyState>}
              {caseTab === 'completed' && !reportsLoading && filteredReports.some((item) => !item.success || item.status !== 'completed') && (
                <div className="secondary-records">
                  <h3>Other saved outcomes</h3>
                  {listReports(filteredReports.filter((item) => !item.success || item.status !== 'completed'))}
                </div>
              )}
            </section>
          )}

          {page === 'patients' && (
            <section className="surface">
              <div className="section-head">
                <div><h2>Patient-linked studies</h2><p>Identifiers below come only from your account-owned report metadata.</p></div>
                <span className="data-scope">No patient registry connected</span>
              </div>
              <div className="tabs" role="tablist" aria-label="Patient views">
                {([['overview', 'Overview'], ['studies', 'MRI Studies'], ['history', 'History']] as const).map(([key, label]) => (
                  <button type="button" role="tab" aria-selected={patientTab === key} onClick={() => setPatientTab(key)} key={key}>{label}</button>
                ))}
              </div>
              {showPatientView()}
            </section>
          )}

          {page === 'viewer' && (
            working
              ? <LoadingView filename={file?.name} />
              : result
                ? <ResultsDashboard response={result} file={file} onReset={() => { setResult(null); setFile(null); setError(null); }} />
                : <div className="viewer-layout">
                  <section className="surface upload-surface">
                    <div className="section-head"><div><h2>Open a study file</h2><p>Choose a supported input and research processing method.</p></div></div>
                    <FileUpload onFileSubmit={analyze} isLoading={working} />
                  </section>
                  <aside className="surface viewer-guidance">
                    <p className="eyebrow">INPUT & MODEL SCOPE</p>
                    <h2>Before analysis</h2>
                    <p>Baseline processing accepts DICOM, NIfTI, common 2D images, and NumPy arrays. Research segmentation accepts a brain FLAIR NIfTI volume only.</p>
                    <div className="viewer-guidance-rule" />
                    <p>The sequence is declared by the uploader; it cannot be independently established from NIfTI pixel data.</p>
                    <p>Medical-image formats without a browser-safe preview remain available to download and inspect in a dedicated DICOM/NIfTI viewer.</p>
                    <div className="viewer-tool-availability">
                      <strong>Viewer tools</strong>
                      <span>Zoom · pan · display contrast</span>
                      <small>Calibrated DICOM window/level, measurements, and annotation drawing are not available here.</small>
                    </div>
                  </aside>
                </div>
          )}

          {page === 'reports' && (
            result
              ? <ResultsDashboard response={result} file={file} onReset={() => { setResult(null); setFile(null); }} />
              : <section className="surface">
                <div className="section-head section-head-wrap">
                  <div><h2>Report library</h2><p>AI output and user-authored review notes remain separate.</p></div>
                  <label className="search-box"><span className="sr-only">Search filename or ID</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search filename or ID" /></label>
                </div>
                <div className="tabs" role="tablist" aria-label="Report state">
                  {([['draft', 'AI Draft'], ['edit', 'Edit'], ['final', 'Final']] as const).map(([key, label]) => (
                    <button type="button" role="tab" aria-selected={reportTab === key} onClick={() => setReportTab(key)} key={key}>{label}</button>
                  ))}
                </div>
                {reportTab === 'draft'
                  ? reportsLoading
                    ? <p className="inline-loading" role="status">Loading reports…</p>
                    : listReports(filteredReports)
                  : reportTab === 'edit'
                    ? <EmptyState title="Edits are recorded as review notes">Open a saved report to add or update a role-authorized, versioned note. The original AI response is retained unchanged.</EmptyState>
                    : <EmptyState title="No finalized reports">The backend does not provide report approval, signing, or finalization. All analysis output remains a research draft.</EmptyState>}
              </section>
          )}

          {page === 'settings' && (
            <section className="surface narrow">
              <div className="section-head"><div><h2>Account profile</h2><p>Profession is self-declared; role is the server-assigned authorization level.</p></div></div>
              <form className="settings-form" onSubmit={(event) => void saveProfile(event)}>
                <label>Full name<input value={name} maxLength={255} onChange={(event) => setName(event.target.value)} /></label>
                <label>Email<input value={user?.email || ''} readOnly /></label>
                <label>Profession<input value={user?.profession.replaceAll('_', ' ') || ''} readOnly /></label>
                <label>Access role<input value={user?.role || ''} readOnly /></label>
                <div className="settings-divider"><strong>Change password</strong><span>Leave both fields empty to keep the current password.</span></div>
                <label>Current password<input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required={!!newPassword} /></label>
                <label>New password<input type="password" autoComplete="new-password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required={!!currentPassword} /></label>
                <button className="primary-link" type="submit">Save changes</button>
              </form>
              {profileMessage && <p className="inline-message" role="status">{profileMessage}</p>}
            </section>
          )}

          {page === 'admin' && adminPage}
        </main>
        <footer className="workspace-footer">MRI AI SYSTEM <span>Research use only · Not for clinical decisions</span></footer>
      </div>
    </div>
  );
}
