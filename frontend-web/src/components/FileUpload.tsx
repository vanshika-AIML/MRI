import React, { useState, useRef } from 'react';
import type { AnalysisOptions } from '../types/analysis';

interface FileUploadProps {
  onFileSubmit: (file: File, options: AnalysisOptions) => void;
  isLoading: boolean;
}

const SUPPORTED_EXTENSIONS = ['.dcm', '.dicom', '.nii', '.nii.gz', '.png', '.jpg', '.jpeg', '.bmp', '.npy', '.npz'];
const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024; // 100MB

export const FileUpload: React.FC<FileUploadProps> = ({ onFileSubmit, isLoading }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showOptions, setShowOptions] = useState(false);
  const [flairSequenceConfirmed, setFlairSequenceConfirmed] = useState(false);

  // Pipeline options state
  const [options, setOptions] = useState<AnalysisOptions>({
    analysis_method: 'baseline',
    normalize: true,
    normalization_method: 'minmax',
    enable_enhancement: true,
    enhancement_methods: ['clahe'],
    enable_detection: true,
    detection_methods: ['intensity_anomaly'],
    confidence_threshold: 0.3,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): boolean => {
    setValidationError(null);
    if (!file || file.size === 0) {
      setValidationError('Selected file is empty (0 bytes). Please choose a valid MRI scan.');
      return false;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setValidationError('File size exceeds the 100MB maximum limit.');
      return false;
    }
    const nameLower = file.name.toLowerCase();
    const isSupported = SUPPORTED_EXTENSIONS.some((ext) => nameLower.endsWith(ext));
    if (!isSupported) {
      setValidationError(
        `Unsupported file format '${file.name}'. Supported formats: DICOM (.dcm), NIfTI (.nii, .nii.gz), Image (.png, .jpg), NumPy (.npy, .npz).`
      );
      return false;
    }
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      } else {
        setSelectedFile(null);
      }
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      } else {
        setSelectedFile(null);
      }
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFile && !isLoading) {
      if (
        options.analysis_method === 'research_flair_segmentation' &&
        !selectedFile.name.toLowerCase().endsWith('.nii') &&
        !selectedFile.name.toLowerCase().endsWith('.nii.gz')
      ) {
        setValidationError('Research segmentation requires a FLAIR volume in NIfTI format (.nii or .nii.gz).');
        return;
      }
      if (
        options.analysis_method === 'research_flair_segmentation' &&
        !flairSequenceConfirmed
      ) {
        setValidationError('Confirm that this is a brain FLAIR volume before running research segmentation.');
        return;
      }
      onFileSubmit(selectedFile, {
        ...options,
        flair_sequence_confirmed: flairSequenceConfirmed,
      });
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFormatBadge = (filename: string): string => {
    const lower = filename.toLowerCase();
    if (lower.endsWith('.dcm') || lower.endsWith('.dicom')) return 'DICOM';
    if (lower.endsWith('.nii') || lower.endsWith('.nii.gz')) return 'NIfTI 3D';
    if (lower.endsWith('.npy') || lower.endsWith('.npz')) return 'NumPy Array';
    return '2D Image';
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Drag & Drop Card */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all cursor-pointer ${
            isDragOver
              ? 'border-cyan-400 bg-cyan-950/30 scale-[1.01]'
              : selectedFile
              ? 'border-emerald-500/60 bg-emerald-950/20'
              : 'border-slate-700 bg-slate-900/60 hover:border-slate-500 hover:bg-slate-800/40'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".dcm,.dicom,.nii,.nii.gz,.png,.jpg,.jpeg,.bmp,.npy,.npz"
            className="hidden"
          />

          {!selectedFile ? (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-cyan-400 shadow-xl">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.8}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 0115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
              </div>

              <div>
                <p className="text-lg font-semibold text-white">
                  Drop your MRI scan here or <span className="text-cyan-400 underline">browse files</span>
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Supports DICOM (.dcm), NIfTI 3D (.nii, .nii.gz), Image (.png, .jpg), and NumPy (.npy, .npz)
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                {['DICOM (.dcm)', 'NIfTI 3D (.nii.gz)', 'Image (.png/.jpg)', 'NumPy (.npy)'].map((tag) => (
                  <span
                    key={tag}
                    className="px-2.5 py-1 rounded-md bg-slate-800/90 text-slate-300 text-xs font-mono border border-slate-700/60"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-slate-800/80 rounded-xl border border-slate-700 text-left">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center font-bold text-xs uppercase">
                  {getFormatBadge(selectedFile.name)}
                </div>
                <div>
                  <h4 className="font-semibold text-white text-sm sm:text-base truncate max-w-md">
                    {selectedFile.name}
                  </h4>
                  <p className="text-xs text-slate-400">
                    Size: {formatFileSize(selectedFile.size)} • Format: {getFormatBadge(selectedFile.name)}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  setValidationError(null);
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-700/60 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
              >
                Change File
              </button>
            </div>
          )}
        </div>

        {/* Validation Error Banner */}
        {validationError && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-3">
            <svg className="w-5 h-5 flex-shrink-0 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{validationError}</span>
          </div>
        )}

        {/* Pipeline Configuration Accordion */}
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-4">
          <button
            type="button"
            onClick={() => setShowOptions(!showOptions)}
            className="w-full flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-white transition"
          >
            <span className="flex items-center space-x-2">
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              </svg>
              <span>Analysis Configuration</span>
            </span>
            <span>{showOptions ? '▲ Hide' : '▼ Expand'}</span>
          </button>

          {showOptions && (
            <div className="mt-4 pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="space-y-2 p-3 bg-slate-800/40 rounded-lg md:col-span-2">
                <label htmlFor="analysis-method" className="block font-medium text-slate-200">
                  Analysis method
                </label>
                <select
                  id="analysis-method"
                  value={options.analysis_method}
                  onChange={(e) =>
                    {
                      setOptions({
                        ...options,
                        analysis_method: e.target.value as AnalysisOptions['analysis_method'],
                      });
                      setFlairSequenceConfirmed(false);
                    }
                  }
                  className="w-full bg-slate-800 border border-slate-700 rounded-md px-2.5 py-2 text-slate-300"
                >
                  <option value="baseline">Baseline heuristic (unvalidated signal analysis)</option>
                  <option value="research_flair_segmentation">Experimental FLAIR whole-tumor segmentation</option>
                </select>
                {options.analysis_method === 'research_flair_segmentation' && (
                  <div className="space-y-2">
                    <p className="text-amber-300">
                      Requires a 3D NIfTI FLAIR scan (.nii or .nii.gz). Sequence identity cannot be verified from NIfTI voxel data.
                    </p>
                    <label className="flex items-start gap-2 text-slate-200">
                      <input
                        type="checkbox"
                        checked={flairSequenceConfirmed}
                        onChange={(event) => setFlairSequenceConfirmed(event.target.checked)}
                        className="mt-0.5 accent-cyan-500"
                      />
                      <span>I confirm this is a brain FLAIR volume. This declaration is not independently verified.</span>
                    </label>
                    <p className="text-amber-300">Research-only; not for patient care.</p>
                  </div>
                )}
              </div>
              {/* Normalization */}
              <div className="space-y-2 p-3 bg-slate-800/40 rounded-lg">
                <label className="flex items-center justify-between font-medium text-slate-200">
                  <span>Intensity Normalization</span>
                  <input
                    type="checkbox"
                    checked={options.normalize}
                    disabled={options.analysis_method !== 'baseline'}
                    onChange={(e) => setOptions({ ...options, normalize: e.target.checked })}
                    className="accent-cyan-500"
                  />
                </label>
                <select
                  value={options.normalization_method}
                  onChange={(e) =>
                    setOptions({ ...options, normalization_method: e.target.value as 'minmax' | 'zscore' })
                  }
                  disabled={!options.normalize || options.analysis_method !== 'baseline'}
                  className="w-full bg-slate-800 border border-slate-700 rounded-md px-2.5 py-1 text-slate-300 disabled:opacity-50"
                >
                  <option value="minmax">Min-Max Scaling (0.0 to 1.0)</option>
                  <option value="zscore">Z-score (Zero Mean, Unit Variance)</option>
                </select>
              </div>

              {/* Enhancement */}
              <div className="space-y-2 p-3 bg-slate-800/40 rounded-lg">
                <label className="flex items-center justify-between font-medium text-slate-200">
                  <span>Image Enhancement Stage</span>
                  <input
                    type="checkbox"
                    checked={options.enable_enhancement}
                    disabled={options.analysis_method !== 'baseline'}
                    onChange={(e) => setOptions({ ...options, enable_enhancement: e.target.checked })}
                    className="accent-cyan-500"
                  />
                </label>
                <select
                  value={options.enhancement_methods?.[0] || 'clahe'}
                  onChange={(e) => setOptions({ ...options, enhancement_methods: [e.target.value] })}
                  disabled={!options.enable_enhancement || options.analysis_method !== 'baseline'}
                  className="w-full bg-slate-800 border border-slate-700 rounded-md px-2.5 py-1 text-slate-300 disabled:opacity-50"
                >
                  <option value="clahe">CLAHE (Contrast Limited Adaptive HistEq)</option>
                  <option value="gaussian_denoise">Gaussian Smoothing Denoising</option>
                  <option value="histogram_equalization">Global Histogram Equalization</option>
                  <option value="unsharp_mask">Unsharp Mask Edge Sharpening</option>
                </select>
              </div>

              {/* Detection */}
              <div className="space-y-2 p-3 bg-slate-800/40 rounded-lg md:col-span-2">
                <label className="flex items-center justify-between font-medium text-slate-200">
                  <span>Baseline Heuristic Candidate Detection</span>
                  <input
                    type="checkbox"
                    checked={options.enable_detection}
                    disabled={options.analysis_method !== 'baseline'}
                    onChange={(e) => setOptions({ ...options, enable_detection: e.target.checked })}
                    className="accent-cyan-500"
                  />
                </label>
                <div className="flex items-center space-x-4">
                  <span className="text-slate-400">Minimum Heuristic Score:</span>
                  <input
                    type="range"
                    min="0.1"
                    max="0.9"
                    step="0.05"
                    value={options.confidence_threshold}
                    onChange={(e) => setOptions({ ...options, confidence_threshold: parseFloat(e.target.value) })}
                    disabled={!options.enable_detection || options.analysis_method !== 'baseline'}
                    className="flex-grow accent-cyan-500 disabled:opacity-50"
                  />
                  <span className="font-mono text-cyan-400 font-semibold">{options.confidence_threshold}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action Button */}
        <button
          type="submit"
          disabled={!selectedFile || isLoading}
          className={`w-full py-4 px-6 rounded-xl font-bold text-sm tracking-wide transition shadow-xl flex items-center justify-center space-x-2 ${
            !selectedFile || isLoading
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
              : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-cyan-500/25 active:scale-[0.99]'
          }`}
        >
          <span>{isLoading ? 'Processing Inference Pipeline...' : 'Analyze MRI Scan'}</span>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      </form>
    </div>
  );
};
