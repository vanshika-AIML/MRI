import React, { useEffect, useRef } from 'react';
import type { DetectedRegion, InputMetadata, SegmentationPrediction } from '../types/analysis';

interface ImageViewerProps {
  file: File | null;
  metadata: InputMetadata;
  detectedRegions: DetectedRegion[];
  prediction?: SegmentationPrediction | null;
}

export const ImageViewer: React.FC<ImageViewerProps> = ({ file, metadata, detectedRegions, prediction }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isRenderableImage = !!file && /\.(png|jpe?g|bmp)$/i.test(file.name);

  useEffect(() => {
    if (prediction) return;
    if (!isRenderableImage || !file || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const imageUrl = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;

      // Draw original scan image
      ctx.drawImage(img, 0, 0);

      // Draw bounding box overlays for detected anomaly regions
      detectedRegions.forEach((region, index) => {
        const [yMin, xMin, yMax, xMax] = region.bbox;
        const width = xMax - xMin;
        const height = yMax - yMin;

        // Choose color based on severity
        const color =
          region.severity === 'high'
            ? '#f43f5e'
            : region.severity === 'medium' || region.severity === 'moderate'
            ? '#f59e0b'
            : '#38bdf8';

        // Draw bounding box
        ctx.strokeStyle = color;
        ctx.lineWidth = Math.max(2, Math.round(canvas.width / 200));
        ctx.strokeRect(xMin, yMin, width, height);

        // Fill subtle background
        ctx.fillStyle = color + '22';
        ctx.fillRect(xMin, yMin, width, height);

        // Draw label tag above box
        ctx.fillStyle = color;
        ctx.font = `bold ${Math.max(12, Math.round(canvas.width / 40))}px sans-serif`;
        const labelText = `#${index + 1} (${(region.confidence * 100).toFixed(0)}%)`;
        ctx.fillText(labelText, xMin, Math.max(14, yMin - 4));
      });
    };
    img.src = imageUrl;
    return () => { img.onload = null; URL.revokeObjectURL(imageUrl); };
  }, [file, isRenderableImage, detectedRegions, prediction]);

  if (prediction) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div>
          <h4 className="font-semibold text-white text-sm">Research segmentation preview</h4>
          <p className="text-xs text-amber-300 mt-1">
            Axial slice {prediction.preview_slice_index} of {prediction.mask_dimensions[2]}; red overlay shows the predicted binary mask.
          </p>
        </div>
        <img
          src={`data:${prediction.overlay_format};base64,${prediction.overlay_png_base64}`}
          alt={`Research segmentation overlay at axial slice ${prediction.preview_slice_index}`}
          loading="lazy"
          decoding="async"
          className="max-h-96 max-w-full mx-auto rounded-lg"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-300">
          <span>{prediction.predicted_voxels.toLocaleString()} predicted voxels · spacing {prediction.voxel_spacing_mm.map((v) => v.toFixed(2)).join(' × ')} mm</span>
          <a
            href={`data:${prediction.mask_format};base64,${prediction.mask_nifti_gz_base64}`}
            download={`mri-${prediction.mask_sha256.slice(0, 12)}-mask.nii.gz`}
            className="rounded-md bg-cyan-700 px-3 py-2 font-semibold text-white hover:bg-cyan-600"
          >
            Download NIfTI mask
          </a>
        </div>
      </div>
    );
  }

  if (!isRenderableImage) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 text-center space-y-3">
        <div className="w-12 h-12 mx-auto rounded-xl bg-slate-800 flex items-center justify-center text-cyan-400 font-bold text-xs uppercase">
          {metadata.source_format}
        </div>
        <div>
          <h4 className="font-semibold text-white text-sm">Volumetric / DICOM Data Source</h4>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            Uploaded format ({metadata.source_format.toUpperCase()}, shape: {metadata.dimensions.join('×')}) processed successfully. Detected region coordinates are detailed below.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-white text-sm flex items-center space-x-2">
          <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <span>Visual Scan View with Bounding Box Overlay</span>
        </h4>
        <span className="text-xs text-slate-400 font-mono">
          {metadata.dimensions.join('×')} px
        </span>
      </div>

      <div className="relative flex justify-center bg-slate-950 rounded-xl overflow-hidden p-2 border border-slate-800">
        <canvas ref={canvasRef} className="max-h-96 w-auto object-contain rounded-lg shadow-2xl" />
      </div>

      {detectedRegions.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          {detectedRegions.map((r, i) => (
            <span
              key={r.region_id || i}
              className={`px-2.5 py-1 rounded-md font-mono border ${
                r.severity === 'high'
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                  : r.severity === 'medium' || r.severity === 'moderate'
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                  : 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
              }`}
            >
              Region #{i + 1}: BBox [{r.bbox.join(', ')}] • Conf: {(r.confidence * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
