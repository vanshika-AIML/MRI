import type { AnalysisResponse } from '../types/analysis';
import type { AnnotationItem } from '../api/analysis';

const escapeHtml = (value: string) => value.replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character] || character);

/** Printable report built from the exact saved API response and separately authored notes. */
export function reportHtml(response: AnalysisResponse, notes: AnnotationItem[]): string {
  const structured = { analysis: response, review_notes: notes };
  const json = JSON.stringify(structured, null, 2);
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MRI research report ${escapeHtml(response.analysis_id)}</title><style>
  @page{size:A4;margin:18mm}body{font:14px/1.55 Arial,sans-serif;color:#17243b;max-width:190mm;margin:auto}
  h1,h2{color:#0b1220}h1{font-size:25px;margin-bottom:2px}h2{font-size:16px;border-bottom:1px solid #d9e1ea;padding-bottom:5px;margin-top:24px}
  .muted{color:#516179}.flag{padding:10px;border-left:4px solid #bc8325;background:#fff9e9}
  dl{display:grid;grid-template-columns:160px 1fr;gap:6px}dt{color:#516179}dd{margin:0;overflow-wrap:anywhere}
  pre{font:9px/1.4 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;page-break-inside:auto}
  .note{border-left:3px solid #2563eb;padding-left:10px;page-break-inside:avoid}section{break-inside:auto}
  </style></head><body><header><h1>MRI AI System</h1><p class="muted">Research analysis report · ${escapeHtml(response.timestamp)}</p></header>
  <p class="flag">Research use only. This analysis cannot establish that a scan is medically normal and must not guide patient care.</p>
  <section><h2>Analysis</h2><dl><dt>Report ID</dt><dd>${escapeHtml(response.analysis_id)}</dd><dt>Source</dt><dd>${escapeHtml(response.input_metadata.filename)}</dd><dt>Method</dt><dd>${escapeHtml(response.model_name)} / ${escapeHtml(response.model_version)}</dd><dt>Mode</dt><dd>${response.is_baseline ? 'Heuristic indicators' : 'Experimental segmentation'}</dd><dt>Status</dt><dd>${escapeHtml(response.success ? response.status : 'Unable to assess reliably')}</dd><dt>Supported target</dt><dd>${escapeHtml(response.prediction?.target || 'No trained diagnostic target')}</dd></dl></section>
  <section><h2>Findings</h2><p>${escapeHtml(response.summary)}</p><p>Candidate regions: ${response.detected_regions_count}; predicted voxels: ${response.prediction?.predicted_voxels ?? 'not available'}.</p></section>
  <section><h2>Review notes</h2>${notes.length ? notes.map(note => `<p class="note"><strong>User note · ${escapeHtml(note.created_at)}</strong><br>${escapeHtml(note.annotation_text)}</p>`).join('') : '<p>No review notes recorded.</p>'}</section>
  <section><h2>Limitations</h2><p>${escapeHtml(response.clinical_disclaimer)}</p>${response.warnings.map(warning => `<p>${escapeHtml(warning)}</p>`).join('')}</section>
  <section><h2>Structured data appendix</h2><pre>${escapeHtml(json)}</pre></section></body></html>`;
}

export function downloadReport(response: AnalysisResponse, notes: AnnotationItem[], format: 'json' | 'html'): void {
  const name = `mri-report-${response.analysis_id}.${format}`;
  const content = format === 'json' ? JSON.stringify({ analysis: response, review_notes: notes }, null, 2) : reportHtml(response, notes);
  const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/html' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = name; anchor.style.display = 'none';
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
