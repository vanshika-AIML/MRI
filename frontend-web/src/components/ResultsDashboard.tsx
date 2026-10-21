import { useEffect, useState, type FormEvent } from 'react';
import type { AnalysisResponse } from '../types/analysis';
import { createAnalysisAnnotation, getAnalysisAnnotations, type AnnotationItem } from '../api/analysis';
import { useAuth } from '../contexts/useAuth';
import { ImageViewer } from './ImageViewer';
import { downloadReport } from './reportExport';

interface Props { response: AnalysisResponse; file: File | null; onReset: () => void }

export function ResultsDashboard({ response, file, onReset }: Props) {
  const { user } = useAuth();
  const [notes, setNotes] = useState<AnnotationItem[]>([]);
  const [note, setNote] = useState('');
  const [noteError, setNoteError] = useState<string | null>(null);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const canAnnotate = user?.role === 'radiologist' || user?.role === 'admin';
  useEffect(() => {
    let current = true;
    void getAnalysisAnnotations(response.analysis_id)
      .then(data => { if (current) setNotes(data); })
      .catch(reason => { if (current) setNotesError(reason instanceof Error ? reason.message : 'Notes unavailable.'); });
    return () => { current = false; };
  }, [response.analysis_id]);
  const addNote = async (event: FormEvent) => {
    event.preventDefault();
    if (!note.trim()) return;
    setSaving(true); setNoteError(null);
    try {
      const saved = await createAnalysisAnnotation(response.analysis_id, note.trim());
      setNotes(current => [...current, saved]); setNote(''); setMessage('Review note saved.');
    } catch (reason) { setNoteError(reason instanceof Error ? reason.message : 'Could not save note.'); }
    finally { setSaving(false); }
  };
  const exportFile = (format: 'json' | 'html') => {
    try { downloadReport(response, notes, format); setMessage(`${format.toUpperCase()} download started.`); }
    catch { setMessage('Could not create the report download.'); }
  };
  const inconclusive = !response.success || response.status === 'failed';
  const outcome = inconclusive ? 'Unable to assess reliably' : response.prediction
    ? 'Experimental segmentation ready' : response.detected_regions_count > 0
      ? 'Candidate regions flagged' : 'No candidate regions flagged';
  const summary = inconclusive ? response.error_message || 'We could not analyze this scan. Check the file and try again.'
    : response.is_baseline && response.detected_regions_count === 0
      ? 'The heuristic returned no candidate regions. This does not establish that the scan is normal.'
      : response.summary;
  return <div className="report-review">
    <div className="report-toolbar"><div><p className="eyebrow">RESEARCH REPORT / {response.analysis_id.slice(0, 8)}</p><h2>Analysis findings</h2><p>Generated {new Date(response.timestamp).toLocaleString()}</p></div><div className="toolbar-actions"><button type="button" onClick={() => exportFile('html')}>Download HTML</button><button type="button" onClick={() => exportFile('json')}>Download JSON report</button><button type="button" onClick={onReset}>Analyze another scan</button></div></div>
    {message && <p className="notice" role="status">{message}</p>}
    <div className={`finding-banner ${inconclusive ? 'finding-error' : 'finding-research'}`}><div><p className="eyebrow">ASSESSMENT STATUS</p><h3>{outcome}</h3><p>{summary}</p></div><span>{response.is_baseline ? 'Heuristic processing' : 'Research segmentation'}</span></div>
    <div className="report-stats"><div><small>Candidate regions</small><strong>{response.detected_regions_count}</strong></div><div><small>Predicted voxels</small><strong>{response.prediction?.predicted_voxels.toLocaleString() ?? '—'}</strong></div><div><small>Execution</small><strong>{response.total_duration_ms.toFixed(0)} ms</strong></div><div><small>Review status</small><strong>AI draft</strong></div></div>
    <div className="report-grid"><section className="surface scan-surface"><div className="section-head"><div><h3>MRI viewer</h3><p>Original, findings and available comparison views</p></div></div><ImageViewer file={file} metadata={response.input_metadata} detectedRegions={response.detected_regions} prediction={response.prediction} /></section><aside className="surface report-details"><h3>Scan & model</h3><dl><dt>Filename</dt><dd>{response.input_metadata.filename}</dd><dt>Format</dt><dd>{response.input_metadata.source_format}</dd><dt>Dimensions</dt><dd>{response.input_metadata.dimensions.join(' × ')}</dd><dt>Model</dt><dd>{response.model_name.replaceAll('_', ' ')}</dd><dt>Version</dt><dd>{response.model_version}</dd><dt>Supported target</dt><dd>{response.prediction?.target || 'No trained diagnostic target'}</dd></dl>{response.prediction && <p className="small-note">Sequence was declared by the uploader; it was not verified from NIfTI pixels.</p>}</aside></div>
    <section className="surface"><div className="section-head"><div><h3>Findings & processing</h3><p>Model output is separate from user-authored review notes.</p></div></div>{response.detected_regions.length ? <div className="finding-list">{response.detected_regions.map(region => <div key={region.region_id}><strong>Candidate region</strong><span>Slice {region.slice_index ?? '2D'} · box [{region.bbox.join(', ')}] · heuristic score {(region.confidence * 100).toFixed(0)}%</span></div>)}</div> : <p className="small-note">{response.prediction ? 'Binary mask is available in the viewer. Region summaries are not generated for this model.' : 'No candidate regions are available. This is not medical clearance.'}</p>}<div className="stage-list">{response.stage_results.map(stage => <div key={stage.stage}><span>{stage.stage.replaceAll('_',' ')}</span><strong className={stage.success ? '' : 'stage-failed'}>{stage.success ? 'Completed' : 'Failed'}</strong><small>{stage.duration_ms.toFixed(1)} ms</small></div>)}</div></section>
    <section className="surface"><div className="section-head"><div><h3>Review notes</h3><p>Saved notes are authored by an authorized user and do not alter AI output.</p></div></div>{notesError && <p className="notice error" role="alert">{notesError}</p>}{notes.length ? <div className="notes-list">{notes.map(item => <article key={item.id}><strong>User review note · v{item.version}</strong><time>{new Date(item.created_at).toLocaleString()}</time><p>{item.annotation_text}</p></article>)}</div> : <p className="small-note">No review notes saved for this report.</p>}{canAnnotate ? <form className="note-form" onSubmit={addNote}><label htmlFor="review-note">Add review note</label><textarea id="review-note" value={note} maxLength={5000} onChange={event => setNote(event.target.value)} placeholder="Record an observation for human review" /><button className="primary-link" type="submit" disabled={saving || !note.trim()}>{saving ? 'Saving…' : 'Save note'}</button>{noteError && <p role="alert">{noteError}</p>}</form> : <p className="small-note">Your role permits reading this report. Radiologist or administrator access is required to add notes.</p>}</section>
    <section className="surface limitation"><h3>Research limitations</h3><p>{response.clinical_disclaimer}</p>{response.warnings.map((warning, index) => <p key={index}>{warning}</p>)}<p>Report ID: {response.analysis_id}</p></section>
  </div>;
}
