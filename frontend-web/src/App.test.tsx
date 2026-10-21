import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App, { MainApp } from './App';
import { AuthContext } from './contexts/useAuth';
import type { AnalysisResponse } from './types/analysis';
import type { UserPublicResponse } from './types/auth';
import { authenticatedJson } from './api/auth';
import type { ReportSummary } from './api/analysis';
import { reportHtml } from './components/reportExport';

const user: UserPublicResponse = { id: 'user-1', username: 'researcher', email: 'r@example.org', full_name: 'Research User', role: 'viewer', profession: 'researcher', is_active: true, is_verified: false };
const report: AnalysisResponse = {
  analysis_id: 'abc123', status: 'completed', success: true, timestamp: '2026-10-16T12:00:00Z',
  input_metadata: { filename: 'brain_scan.dcm', source_format: 'dicom', dimensions: [128,128], ndim: 2, modality: 'MR' },
  model_name: 'baseline_mri_pipeline', model_version: '1.0.0', is_baseline: true, total_duration_ms: 48,
  severity: 'not_assessed', overall_confidence: .75, detected_regions_count: 1,
  detected_regions: [{ region_id: 'one', bbox: [20,20,40,40], centroid: [30,30], area_pixels: 400, mean_intensity: 100, max_intensity: 240, anomaly_score: .75, confidence: .75, severity: 'moderate' }],
  stage_results: [{ stage: 'preprocessing', success: true, duration_ms: 7, details: {} }], summary: 'One candidate region for research review.', warnings: [], clinical_disclaimer: 'Experimental only.',
};
const summary = { analysis_id: report.analysis_id, timestamp: report.timestamp, filename: report.input_metadata.filename, model_name: report.model_name, is_baseline: true, success: true, status: 'completed', has_prediction: false };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const navigate = async (page: string) => act(async () => { window.location.hash = `#/${page}`; window.dispatchEvent(new HashChangeEvent('hashchange')); });
function authenticated(role: UserPublicResponse['role'] = 'viewer') {
  render(<AuthContext.Provider value={{ user: { ...user, role }, isAuthenticated: true, isLoading: false, error: null, login: async () => {}, logout: async () => {}, register: async () => user, clearError: () => {}, refreshUser: async () => {} }}><MainApp /></AuthContext.Provider>);
}
function mockApi(analysis: AnalysisResponse = report, reports: ReportSummary[] = [summary]) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input, options) => {
    const path = String(input);
    if (path.endsWith('/api/v1/health')) return Promise.resolve(json({ status: 'ok' }));
    if (path.endsWith('/api/v1/analysis/reports')) return Promise.resolve(json(reports));
    if (path.endsWith('/api/v1/analysis') && options?.method === 'POST') return Promise.resolve(json(analysis));
    if (path.endsWith('/api/v1/analysis/abc123/report')) return Promise.resolve(json(analysis));
    if (path.endsWith('/api/v1/analysis/abc123/annotations')) return Promise.resolve(json([]));
    if (path.includes('/api/v1/auth/users/') && path.endsWith('/role?role=radiologist')) return Promise.resolve(json({ ...user, role: 'radiologist' }));
    return Promise.reject(new Error(`Unexpected request: ${path}`));
  });
}

describe('MRI research workspace', () => {
  beforeEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); window.location.hash = '#/dashboard'; });

  it('starts with authentication and retains profession and password controls', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: 'MRI Analysis' })).toBeDefined();
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Create account/i }));
    expect(screen.getByLabelText(/Profession/i)).toBeDefined();
    fireEvent.click(screen.getAllByRole('button', { name: 'Show password' })[0]);
    expect((document.querySelector('#reg-password') as HTMLInputElement).type).toBe('text');
  });

  it('shows real owned counts and navigates all available sections', async () => {
    mockApi(); authenticated();
    await waitFor(() => expect(screen.getByText('brain_scan.dcm')).toBeDefined());
    expect(screen.getByText('Research masks')).toBeDefined();
    await navigate('cases');
    expect(screen.getByRole('heading', { name: 'Cases' })).toBeDefined();
    fireEvent.change(screen.getByPlaceholderText('Search filename or ID'), { target: { value: 'no-match' } });
    expect(screen.getByText('No completed analyses')).toBeDefined();
    fireEvent.click(screen.getByRole('tab', { name: 'Pending' }));
    expect(screen.getByText('No pending queue is available')).toBeDefined();
    fireEvent.click(screen.getByRole('tab', { name: 'In review' }));
    expect(screen.getByText('No review queue is available')).toBeDefined();
    await navigate('patients');
    expect(screen.getByText('No linked patients')).toBeDefined();
    fireEvent.change(screen.getByPlaceholderText('Search workspace'), { target: { value: '' } });
    await navigate('reports');
    expect(screen.getByText('brain_scan.dcm')).toBeDefined();
    fireEvent.click(screen.getByRole('tab', { name: 'Final' }));
    expect(screen.getByText('No finalized reports')).toBeDefined();
  });

  it('restricts the admin page in navigation for viewers', async () => {
    mockApi(); authenticated();
    expect(screen.queryByRole('link', { name: /Admin Panel/ })).toBeNull();
    await navigate('admin');
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeDefined();
    expect(screen.queryByRole('heading', { name: 'Role management' })).toBeNull();
  });

  it('shows only patient identifiers present in owned report metadata', async () => {
    mockApi(report, [{ ...summary, patient_id: 'synthetic-patient-id' }]);
    authenticated();
    await navigate('patients');
    await waitFor(() => expect(screen.getByText('synthetic-patient-id')).toBeDefined());
    expect(screen.getByRole('tab', { name: 'Overview' }).getAttribute('aria-selected')).toBe('true');
    fireEvent.click(screen.getByRole('tab', { name: 'MRI Studies' }));
    expect(screen.getByText('brain_scan.dcm')).toBeDefined();
    fireEvent.click(screen.getByRole('tab', { name: 'History' }));
    expect(screen.getByRole('button', { name: 'Open report' })).toBeDefined();
  });

  it('allows administrators to update a role through the protected backend route', async () => {
    const fetchSpy = mockApi();
    sessionStorage.setItem('mri_access_token', 'test-admin-token');
    authenticated('admin');
    await navigate('admin');
    fireEvent.change(screen.getByLabelText('User ID'), { target: { value: 'user-2' } });
    fireEvent.change(screen.getByLabelText('Authorization role'), { target: { value: 'radiologist' } });
    fireEvent.click(screen.getByRole('button', { name: 'Update role' }));
    await waitFor(() => expect(screen.getByText('researcher is now radiologist.')).toBeDefined());
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/users/user-2/role?role=radiologist'),
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({ Authorization: 'Bearer test-admin-token' }),
      }),
    );
    expect(screen.getByText(/audit-log endpoint are not available/i)).toBeDefined();
  });

  it('opens the authorized report and renders model output, viewer tabs, and limitations', async () => {
    mockApi(); authenticated();
    await waitFor(() => expect(screen.getByText('brain_scan.dcm')).toBeDefined());
    fireEvent.click(screen.getByRole('button', { name: /brain_scan.dcm/ }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Analysis findings' })).toBeDefined());
    expect(screen.getByText('Candidate regions flagged')).toBeDefined();
    expect(screen.getByRole('tab', { name: 'AI Findings' })).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'W/L' }));
    expect(screen.getByRole('status', { name: 'Viewer tool status' }).textContent).toContain('Calibrated DICOM window/level is not available');
    expect(screen.getByText('Experimental only.')).toBeDefined();
    expect(screen.getByText(/Radiologist or administrator access is required/)).toBeDefined();
  });

  it('uploads from the viewer and never labels an empty heuristic scan normal', async () => {
    mockApi({ ...report, detected_regions: [], detected_regions_count: 0, severity: 'normal', summary: 'Detection: no abnormalities flagged.' });
    authenticated(); await navigate('viewer');
    fireEvent.change(document.querySelector('input[type="file"]') as HTMLInputElement, { target: { files: [new File(['synthetic'], 'scan.dcm')] } });
    fireEvent.click(screen.getByRole('button', { name: /Analyze MRI Scan/i }));
    await waitFor(() => expect(screen.getByText('No candidate regions flagged')).toBeDefined());
    expect(screen.getAllByText(/does not establish that the scan is normal/i).length).toBeGreaterThan(0);
    expect(screen.queryByText('Detection: no abnormalities flagged.')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Analyze another scan/i }));
    expect(screen.getByText(/Drop your MRI scan here/i)).toBeDefined();
  });

  it('shows upload validation and server failure without a reassuring result', async () => {
    mockApi(); authenticated(); await navigate('viewer');
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(['x'], 'paper.pdf')] } });
    expect(screen.getByText(/Unsupported file format/)).toBeDefined();
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => String(path).endsWith('/api/v1/analysis') ? Promise.resolve(json({ error: { message: 'Corrupt DICOM' } }, 400)) : Promise.resolve(json([])));
    fireEvent.change(input, { target: { files: [new File(['x'], 'scan.dcm')] } });
    fireEvent.click(screen.getByRole('button', { name: /Analyze MRI Scan/i }));
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Corrupt DICOM'));
    expect(screen.queryByText('Candidate regions flagged')).toBeNull();
  });

  it('produces printable HTML with escaped data and structured JSON appendix', () => {
    const html = reportHtml({ ...report, summary: '<script>alert(1)</script>' }, []);
    expect(html).toContain('<!doctype html>');
    expect(html).toContain('Structured data appendix');
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('abc123');
  });

  it('downloads the report through the page in JSON and HTML formats', async () => {
    mockApi(); authenticated(); await navigate('viewer');
    fireEvent.change(document.querySelector('input[type="file"]') as HTMLInputElement, { target: { files: [new File(['x'], 'scan.dcm')] } });
    fireEvent.click(screen.getByRole('button', { name: /Analyze MRI Scan/i }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Analysis findings' })).toBeDefined());
    const create = vi.fn(() => 'blob:test');
    const clicked: string[] = [];
    vi.stubGlobal('URL', { createObjectURL: create, revokeObjectURL: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function(this: HTMLAnchorElement) { clicked.push(this.download); });
    fireEvent.click(screen.getByRole('button', { name: 'Download JSON report' }));
    fireEvent.click(screen.getByRole('button', { name: 'Download HTML' }));
    expect(clicked).toEqual(['mri-report-abc123.json', 'mri-report-abc123.html']);
    expect(create.mock.calls).toHaveLength(2);
  });

  it('clears rejected credentials and signals the authenticated UI when refresh expires', async () => {
    sessionStorage.setItem('mri_access_token', 'test-access-token');
    sessionStorage.setItem('mri_refresh_token', 'test-refresh-token');
    const expired = vi.fn();
    window.addEventListener('mri:session-expired', expired);
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'Refresh token revoked.' }, 401));
    await expect(authenticatedJson('/api/v1/analysis/reports')).rejects.toThrow('Refresh token revoked.');
    expect(sessionStorage.getItem('mri_access_token')).toBeNull();
    expect(sessionStorage.getItem('mri_refresh_token')).toBeNull();
    expect(expired).toHaveBeenCalledTimes(1);
    window.removeEventListener('mri:session-expired', expired);
  });
});
