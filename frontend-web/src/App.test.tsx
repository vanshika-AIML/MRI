import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App, { MainApp } from './App';
import { AuthContext } from './contexts/useAuth';
import type { AnalysisResponse } from './types/analysis';

const MOCK_SUCCESS_RESPONSE: AnalysisResponse = {
  analysis_id: 'test-job-uuid-12345',
  status: 'completed',
  success: true,
  timestamp: '2026-09-28T12:00:00Z',
  input_metadata: {
    filename: 'brain_scan.dcm',
    source_format: 'dicom',
    dimensions: [128, 128],
    ndim: 2,
    modality: 'MR',
    patient_id: 'PATIENT-999',
  },
  model_name: 'baseline_mri_pipeline',
  model_version: '1.0.0',
  is_baseline: true,
  total_duration_ms: 45.2,
  severity: 'medium',
  overall_confidence: 0.75,
  detected_regions_count: 1,
  detected_regions: [
    {
      region_id: 'region_intensity_0',
      bbox: [20, 20, 40, 40],
      centroid: [30.0, 30.0],
      area_pixels: 400,
      mean_intensity: 245.0,
      max_intensity: 255.0,
      anomaly_score: 0.75,
      confidence: 0.75,
      severity: 'medium',
    },
  ],
  stage_results: [
    { stage: 'preprocessing', success: true, duration_ms: 5.0, details: {} },
    { stage: 'enhancement', success: true, duration_ms: 15.0, details: {} },
    { stage: 'detection', success: true, duration_ms: 25.0, details: {} },
  ],
  summary: 'Pipeline completed. 1 region identified.',
  warnings: [],
  clinical_disclaimer:
    'DISCLAIMER: Baseline analysis tool for technical assessment only. Not for clinical diagnosis.',
};

const TEST_USER = {
    id: 'test-user',
    email: 'researcher@example.com',
    username: 'researcher',
    full_name: null,
    role: 'viewer' as const,
    profession: 'researcher' as const,
    is_active: true,
    is_verified: false,
};

const renderAuthenticatedApp = () =>
    render(
      <AuthContext.Provider
        value={{
          user: TEST_USER,
          isAuthenticated: true,
          isLoading: false,
          error: null,
          login: async () => {},
          logout: async () => {},
          register: async () => TEST_USER,
          clearError: () => {},
          refreshUser: async () => {},
        }}
      >
        <MainApp />
      </AuthContext.Provider>,
    );

describe('MRI Analysis Frontend Workflow Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Renders header and upload UI in idle state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/v1/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
      }
      return Promise.reject(new Error('Unknown endpoint'));
    });

    renderAuthenticatedApp();

    expect(screen.getByText(/MRI Research Workbench/i)).toBeDefined();
    expect(screen.getByText(/Drop your MRI scan here/i)).toBeDefined();
    expect(screen.getByText(/Analyze MRI Scan/i)).toBeDefined();
  });

  it('2. Requires authentication and allows profession selection with password visibility', async () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: 'MRI Analysis' })).toBeDefined();
    expect(screen.queryByText(/Drop your MRI scan here/i)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Create account/i }));
    expect(screen.getByLabelText(/Profession/i)).toBeDefined();

    const showPassword = screen.getAllByRole('button', { name: 'Show password' })[0];
    fireEvent.click(showPassword);
    expect((document.querySelector('#reg-password') as HTMLInputElement).type).toBe('text');
  });

  it('3. Rejects unsupported file extensions with error banner', async () => {
    renderAuthenticatedApp();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const invalidFile = new File(['dummy content'], 'document.pdf', { type: 'application/pdf' });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Unsupported file format 'document.pdf'/i)).toBeDefined();
    });
  });

  it('4. Selects valid file and shows filename preview', async () => {
    renderAuthenticatedApp();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(['valid png bytes'], 'mri_slice.png', { type: 'image/png' });

    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText('mri_slice.png')).toBeDefined();
      expect(screen.getAllByText(/2D Image/i).length).toBeGreaterThan(0);
    });
  });

  it('5. Submits analysis request and displays loading, results, detection, baseline indicator, and disclaimer', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      if (typeof url === 'string' && url.includes('/api/v1/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
      }
      if (typeof url === 'string' && url.includes('/api/v1/analysis')) {
        expect(init?.method).toBe('POST');
        return Promise.resolve(
          new Response(JSON.stringify(MOCK_SUCCESS_RESPONSE), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    renderAuthenticatedApp();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['dummy bytes'], 'scan.dcm', { type: 'application/dicom' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitBtn = screen.getByRole('button', { name: /Analyze MRI Scan/i });
    fireEvent.click(submitBtn);

    // Results render
    await waitFor(() => {
      expect(screen.getByText(/Analysis Findings Dashboard/i)).toBeDefined();
      expect(screen.getByText(/Job ID: test-job-uuid-12345/i)).toBeDefined();
    });

    // Baseline pipeline identity renders
    expect(screen.getAllByText(/Baseline Heuristic Pipeline/i).length).toBeGreaterThan(0);

    // Detection renders
    expect(screen.getByText(/Region #1/i)).toBeDefined();
    expect(screen.getByText(/75%/i)).toBeDefined();

    // Disclaimer renders
    expect(screen.getByText(/Mandatory Clinical Disclaimer/i)).toBeDefined();
    expect(
      screen.getByText(/DISCLAIMER: Baseline analysis tool for technical assessment only/i)
    ).toBeDefined();

    expect(fetchSpy).toHaveBeenCalled();

    const createObjectURL = vi.fn((_blob: Blob) => 'blob:test-report');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    const anchorClick = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(function (this: HTMLAnchorElement) {
        expect(this.download).toBe('mri-test-job-uuid-12345.json');
        expect(this.href).toBe('blob:test-report');
      });
    fireEvent.click(screen.getByRole('button', { name: 'Download JSON report' }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const reportBlob = createObjectURL.mock.calls[0][0];
    expect(reportBlob.type).toBe('application/json');
    await expect(reportBlob.text()).resolves.toBe(JSON.stringify(MOCK_SUCCESS_RESPONSE, null, 2));
    expect(screen.getByRole('status').textContent).toContain('JSON report download started.');
    anchorClick.mockRestore();
    vi.unstubAllGlobals();
  });

  it('6. Handles API error safely', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/v1/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
      }
      if (typeof url === 'string' && url.includes('/api/v1/analysis')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              error: {
                status_code: 400,
                message: 'Corrupt or invalid DICOM file header.',
              },
            }),
            { status: 400, headers: { 'Content-Type': 'application/json' } }
          )
        );
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    renderAuthenticatedApp();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['corrupt data'], 'corrupt.dcm', { type: 'application/dicom' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitBtn = screen.getByRole('button', { name: /Analyze MRI Scan/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Analysis Request Failed/i)).toBeDefined();
      expect(screen.getByText(/Corrupt or invalid DICOM file header/i)).toBeDefined();
    });
  });

  it('7. Reset action clears results and returns to idle state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/v1/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
      }
      if (typeof url === 'string' && url.includes('/api/v1/analysis')) {
        return Promise.resolve(
          new Response(JSON.stringify(MOCK_SUCCESS_RESPONSE), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    renderAuthenticatedApp();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['dummy bytes'], 'scan.dcm', { type: 'application/dicom' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitBtn = screen.getByRole('button', { name: /Analyze MRI Scan/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Analysis Findings Dashboard/i)).toBeDefined();
    });

    const resetBtn = screen.getAllByRole('button', { name: /Analyze Another Scan/i })[0];
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(screen.getByText(/Drop your MRI scan here/i)).toBeDefined();
    });
  });

  it('does not present an empty baseline result as normal', async () => {
    const legacyResult: AnalysisResponse = {
      ...MOCK_SUCCESS_RESPONSE,
      severity: 'normal',
      detected_regions_count: 0,
      detected_regions: [],
      summary: 'Detection: no abnormalities flagged.',
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/v1/health')) {
        return Promise.resolve(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
      }
      if (typeof url === 'string' && url.endsWith('/annotations')) {
        return Promise.resolve(new Response('[]', { status: 200 }));
      }
      if (typeof url === 'string' && url.endsWith('/api/v1/analysis')) {
        return Promise.resolve(
          new Response(JSON.stringify(legacyResult), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    renderAuthenticatedApp();
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: { files: [new File(['dummy bytes'], 'scan.dcm', { type: 'application/dicom' })] },
    });
    fireEvent.click(screen.getByRole('button', { name: /Analyze MRI Scan/i }));

    await waitFor(() => {
      expect(screen.getByText('NOT ASSESSED')).toBeDefined();
      expect(screen.getByText('Heuristic Signal Level')).toBeDefined();
    });
    expect(screen.queryByText('Detection: no abnormalities flagged.')).toBeNull();
    expect(screen.getByText(/does not establish that the scan is normal/i)).toBeDefined();
  });
});
