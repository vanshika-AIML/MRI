import React, { useEffect, useRef, useState } from 'react';
import type { AnalysisResponse } from '../types/analysis';
import { ImageViewer } from './ImageViewer';
import { useAuth } from '../contexts/useAuth';
import {
  getAnalysisAnnotations,
  createAnalysisAnnotation,
  type AnnotationItem,
} from '../api/analysis';

interface ResultsDashboardProps {
  response: AnalysisResponse;
  file: File | null;
  onReset: () => void;
}

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ response, file, onReset }) => {
  const { user } = useAuth();
  const [annotations, setAnnotations] = useState<AnnotationItem[]>([]);
  const [annotationText, setAnnotationText] = useState('');
  const [isSubmittingAnnotation, setIsSubmittingAnnotation] = useState(false);
  const [annotationError, setAnnotationError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimerRef = useRef<number | null>(null);

  const canAnnotate = user && (user.role === 'radiologist' || user.role === 'admin');

  const showToast = (message: string) => {
    setToastMessage(message);
    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current);
    }
    toastTimerRef.current = window.setTimeout(() => {
      setToastMessage(null);
      toastTimerRef.current = null;
    }, 4000);
  };

  useEffect(() => {
    let isMounted = true;
    if (response?.analysis_id) {
      getAnalysisAnnotations(response.analysis_id)
        .then((data) => {
          if (isMounted) setAnnotations(data);
        })
        .catch(() => {
          // silently handle optional db failure
        });
    }
    return () => {
      isMounted = false;
    };
  }, [response?.analysis_id]);

  useEffect(() => () => {
    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current);
    }
  }, []);

  const handleAnnotationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!annotationText.trim() || !response?.analysis_id) return;
    setIsSubmittingAnnotation(true);
    setAnnotationError(null);
    try {
      const created = await createAnalysisAnnotation(
        response.analysis_id,
        annotationText.trim()
      );
      setAnnotations((prev) => [...prev, created]);
      setAnnotationText('');
      showToast('Observation saved.');
    } catch (err) {
      setAnnotationError(err instanceof Error ? err.message : 'Failed to save annotation.');
    } finally {
      setIsSubmittingAnnotation(false);
    }
  };

  const {
    analysis_id,
    status,
    success,
    timestamp,
    input_metadata,
    model_name,
    model_version,
    is_baseline,
    total_duration_ms,
    severity,
    overall_confidence,
    detected_regions_count,
    detected_regions,
    stage_results,
    summary,
    warnings,
    clinical_disclaimer,
  } = response;

  const getSeverityBadgeClass = (sev: string): string => {
    const s = sev.toLowerCase();
    if (s === 'not_assessed' || s === 'normal' || s === 'none') {
      return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
    }
    if (s === 'high') return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
    if (s === 'medium' || s === 'moderate') return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    if (s === 'low') return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
    return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
  };

  const displayedSummary =
    is_baseline && detected_regions.length === 0
      ? 'The baseline heuristic returned no candidate regions. This does not establish that the scan is normal.'
      : summary || 'Inference pipeline completed.';

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 text-left">
      <button type="button" className="px-4 py-2 rounded-lg bg-sky-700 text-white" onClick={() => {
        const url = URL.createObjectURL(new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' }));
        const anchor = document.createElement('a');
        anchor.href = url; anchor.download = `mri-${response.analysis_id}.json`; anchor.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        showToast('JSON report download started.');
      }}>Download JSON report</button>
      {/* Top Banner & Reset Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div>
          <div className="flex items-center space-x-3">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                success ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}
            >
              {status.toUpperCase()}
            </span>
            {is_baseline && (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
                Baseline Heuristic Pipeline
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">Analysis Findings Dashboard</h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Job ID: {analysis_id} • Timestamp: {new Date(timestamp).toLocaleString()}
          </p>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs transition shadow-lg shadow-cyan-500/20 flex items-center justify-center space-x-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Analyze Another Scan</span>
        </button>
      </div>

      {/* Grid Layout: Executive Summary & Input Metadata */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Executive Summary Card */}
        <div className="md:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 flex items-center space-x-2">
            <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Executive Findings Summary</span>
          </h3>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-3 bg-slate-800/40 rounded-xl border border-slate-800">
              <p className="text-xs text-slate-400">
                {is_baseline ? 'Heuristic Signal Level' : 'Assessment Status'}
              </p>
              <p className={`text-sm font-bold mt-1 px-2.5 py-0.5 rounded-md inline-block border ${getSeverityBadgeClass(severity)}`}>
                {severity === 'not_assessed' || severity === 'normal' || severity === 'none'
                  ? 'NOT ASSESSED'
                  : severity.toUpperCase()}
              </p>
            </div>

            <div className="p-3 bg-slate-800/40 rounded-xl border border-slate-800">
              <p className="text-xs text-slate-400">{response.prediction ? 'Predicted Voxels' : 'Peak Anomaly Score'}</p>
              <p className="text-sm font-mono font-bold text-cyan-400 mt-1">
                {response.prediction ? response.prediction.predicted_voxels.toLocaleString() : `${(overall_confidence * 100).toFixed(1)}%`}
              </p>
            </div>

            <div className="p-3 bg-slate-800/40 rounded-xl border border-slate-800">
              <p className="text-xs text-slate-400">Detected Regions</p>
              <p className="text-sm font-mono font-bold text-white mt-1">{detected_regions_count}</p>
            </div>

            <div className="p-3 bg-slate-800/40 rounded-xl border border-slate-800">
              <p className="text-xs text-slate-400">Execution Time</p>
              <p className="text-sm font-mono font-bold text-slate-200 mt-1">{total_duration_ms.toFixed(0)} ms</p>
            </div>
          </div>

          <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 text-xs text-slate-300">
            <span className="font-semibold text-cyan-400">Summary: </span>
            {displayedSummary}
          </div>

          <p className="text-[11px] text-slate-400 italic">
            Research model masks and heuristic scores are experimental, are not clinical probabilities or diagnoses, and must not guide patient care.
          </p>
        </div>

        {/* Input Metadata Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 flex items-center space-x-2">
            <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Scan Input Metadata</span>
          </h3>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Filename:</span>
              <span className="text-white font-mono truncate max-w-[160px]">{input_metadata.filename}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Format:</span>
              <span className="text-cyan-400 font-medium uppercase">{input_metadata.source_format}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Dimensions:</span>
              <span className="text-white font-mono">{input_metadata.dimensions.join(' × ')}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Dimensionality:</span>
              <span className="text-slate-300 font-mono">{input_metadata.ndim}D Array</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Modality:</span>
              <span className="text-slate-200 font-medium">{input_metadata.modality || 'MR'}</span>
            </div>
            {input_metadata.patient_id && (
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Patient ID:</span>
                <span className="text-emerald-400 font-mono">{input_metadata.patient_id}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Image Overlay Visualization Component */}
      <ImageViewer file={file} metadata={input_metadata} detectedRegions={detected_regions} prediction={response.prediction} />

      {/* Pipeline Execution Stages */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 flex items-center space-x-2">
          <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span>Pipeline Stage Execution Metrics</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {stage_results.map((stageItem, idx) => (
            <div key={stageItem.stage || idx} className="p-4 bg-slate-800/40 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                  {stageItem.stage}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  {stageItem.duration_ms.toFixed(1)} ms
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Status: <span className="text-emerald-400 font-medium">Completed</span>
              </p>
              {stageItem.details && Object.keys(stageItem.details).length > 0 && (
                <div className="text-[11px] text-slate-400 bg-slate-950/60 p-2 rounded border border-slate-800/60 font-mono overflow-x-auto">
                  {JSON.stringify(stageItem.details)}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Detected Regions List */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 flex items-center justify-between">
          <span className="flex items-center space-x-2">
            <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>
              {response.prediction
                ? 'Research Segmentation Mask'
                : `Heuristic Candidate Regions (${detected_regions_count})`}
            </span>
          </span>
        </h3>

        {detected_regions.length === 0 ? (
          <div className="p-6 bg-slate-800/30 rounded-xl border border-slate-800 text-center text-xs text-slate-400">
            {response.prediction
              ? 'Research segmentation returns a binary mask rather than candidate-region summaries; review the mask preview separately.'
              : 'No candidate regions are available for display.'}
          </div>
        ) : (
          <div className="space-y-3">
            {detected_regions.map((reg, index) => (
              <div
                key={reg.region_id || index}
                className="p-4 bg-slate-800/40 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-3">
                    <span className="font-bold text-white">Region #{index + 1}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getSeverityBadgeClass(reg.severity)}`}>
                      {reg.severity}
                    </span>
                    {reg.slice_index !== null && reg.slice_index !== undefined && (
                      <span className="text-slate-400 font-mono">Slice Z={reg.slice_index}</span>
                    )}
                  </div>
                  <p className="text-slate-400 font-mono">
                    Bounding Box: [{reg.bbox.join(', ')}] • Centroid: [{reg.centroid.map((n) => n.toFixed(1)).join(', ')}]
                  </p>
                </div>

                <div className="flex items-center space-x-4 text-right">
                  <div>
                    <p className="text-[10px] text-slate-400">Area</p>
                    <p className="font-mono text-white font-semibold">{reg.area_pixels} px</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-400">Mean Intensity</p>
                    <p className="font-mono text-slate-200">{reg.mean_intensity.toFixed(1)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-400">Confidence</p>
                    <p className="font-mono text-cyan-400 font-bold">{(reg.confidence * 100).toFixed(0)}%</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Model Architecture, Provenance & Source Immutability */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 text-xs shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h4 className="font-semibold text-white text-sm flex items-center gap-2">
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Provenance & Source Immutability</span>
            </h4>
            <p className="text-slate-400 text-[11px] mt-0.5">
              Original uploaded scan file remains strictly immutable. All enhancements and derivations maintain cryptographic traceability.
            </p>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-mono text-[11px]">
            Original Protected (Read-Only)
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-slate-300">
          <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-800/80">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Model Pipeline</span>
            <span className="font-mono text-cyan-400 font-bold">{model_name} v{model_version}</span>
          </div>
          <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-800/80">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Execution Duration</span>
            <span className="font-mono text-slate-200">{total_duration_ms.toFixed(1)} ms</span>
          </div>
          <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-800/80">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Status / Mode</span>
            <span className="font-medium text-amber-400">{is_baseline ? 'Baseline Heuristic Engine' : 'Research Segmentation Model'}</span>
          </div>
        </div>
      </div>

      {/* Radiologist Clinical Annotations & Controlled Modification */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h4 className="font-semibold text-white text-sm flex items-center gap-2">
              <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              <span>Clinical Annotations & Observations</span>
            </h4>
            <p className="text-slate-400 text-xs mt-0.5">
              Radiologist observations are audited and clearly distinguished from AI model-generated findings.
            </p>
          </div>
          <span className="text-[11px] px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 font-medium">
            Controlled Audit Trail
          </span>
        </div>

        {/* Existing Annotations List */}
        {annotations.length > 0 ? (
          <div className="space-y-2.5">
            {annotations.map((ann) => (
              <div key={ann.id} className="p-3.5 bg-slate-950/70 rounded-xl border border-indigo-900/40 text-xs space-y-1">
                <div className="flex items-center justify-between text-slate-400 text-[11px]">
                  <span className="inline-flex items-center gap-1.5 font-semibold text-indigo-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                    CLINICAL NOTE (USER ANNOTATION — NOT MODEL FINDING)
                  </span>
                  <span className="font-mono text-slate-400">
                    v{ann.version} • {ann.created_at ? new Date(ann.created_at).toLocaleString() : 'Recent'}
                  </span>
                </div>
                <p className="text-slate-200 mt-1 pl-3 border-l-2 border-indigo-500/60 font-sans leading-relaxed">
                  {ann.annotation_text}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic">
            No clinical annotations recorded for this study yet.
          </p>
        )}

        {/* Annotation Input */}
        {canAnnotate ? (
          <form onSubmit={handleAnnotationSubmit} className="space-y-3 pt-2">
            <label htmlFor="annotation-input" className="block text-xs font-medium text-slate-300">
              Add Radiologist Impression / Verification Note:
            </label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                id="annotation-input"
                type="text"
                value={annotationText}
                onChange={(e) => setAnnotationText(e.target.value)}
                placeholder="e.g. Verified hyperintensity in axial slice 12; non-pathological motion artifact."
                className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                disabled={isSubmittingAnnotation}
              />
              <button
                type="submit"
                disabled={isSubmittingAnnotation || !annotationText.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs transition whitespace-nowrap shadow-md shadow-indigo-600/20"
              >
                {isSubmittingAnnotation ? 'Saving...' : 'Add Clinical Note'}
              </button>
            </div>
            {annotationError && (
              <p className="text-xs text-rose-400 font-medium">{annotationError}</p>
            )}
          </form>
        ) : (
          <div className="p-3 bg-slate-950/40 rounded-xl border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
            <span>
              {user ? (
                <>Your account ({user.role}) has viewer privileges. Sign in as <strong>radiologist</strong> or <strong>admin</strong> to add clinical notes.</>
              ) : (
                <>Sign in as an authorized radiologist or administrator to attach audited clinical annotations.</>
              )}
            </span>
          </div>
        )}
      </div>

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-1">
          <p className="font-semibold">Pipeline Warnings:</p>
          <ul className="list-disc list-inside">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Mandatory Clinical Disclaimer */}
      <div className="p-6 rounded-2xl bg-rose-950/20 border border-rose-500/30 text-rose-200 text-xs space-y-2 shadow-xl">
        <div className="flex items-center space-x-2 font-bold uppercase tracking-wider text-rose-400">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Mandatory Clinical Disclaimer</span>
        </div>
        <p className="leading-relaxed text-slate-300">{clinical_disclaimer}</p>
      </div>

      {/* Bottom Reset Action */}
      <div className="pt-4 text-center">
        <button
          type="button"
          onClick={onReset}
          className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs transition shadow-xl shadow-cyan-500/25"
        >
          Analyze Another MRI Scan
        </button>
      </div>
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-4 right-4 z-50 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white shadow-xl"
        >
          {toastMessage}
        </div>
      )}
    </div>
  );
};
