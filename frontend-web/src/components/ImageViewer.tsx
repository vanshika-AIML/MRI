import { useEffect, useRef, useState, type PointerEvent } from 'react';
import type { DetectedRegion, InputMetadata, SegmentationPrediction } from '../types/analysis';

interface Props {
  file: File | null;
  metadata: InputMetadata;
  detectedRegions: DetectedRegion[];
  prediction?: SegmentationPrediction | null;
}

type Mode = 'original' | 'enhanced' | 'findings' | 'comparison';

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 3;

export function ImageViewer({ file, metadata, detectedRegions, prediction }: Props) {
  const [mode, setMode] = useState<Mode>(prediction ? 'findings' : 'original');
  const [zoom, setZoom] = useState(1);
  const [contrast, setContrast] = useState(1);
  const [panEnabled, setPanEnabled] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [message, setMessage] = useState<string | null>(null);
  const viewerRoot = useRef<HTMLElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const originalCanvas = useRef<HTMLCanvasElement>(null);
  const findingsCanvas = useRef<HTMLCanvasElement>(null);
  const comparisonOriginalCanvas = useRef<HTMLCanvasElement>(null);
  const comparisonFindingsCanvas = useRef<HTMLCanvasElement>(null);
  const dragOrigin = useRef<{ x: number; y: number; offsetX: number; offsetY: number } | null>(null);
  const imageAvailable = !!file && /\.(png|jpe?g|bmp)$/i.test(file.name);

  useEffect(() => {
    if (!file || !imageAvailable) return;
    let active = true;
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      if (!active) return;
      const canvases = [
        { canvas: originalCanvas.current, withFindings: false },
        { canvas: findingsCanvas.current, withFindings: true },
        { canvas: comparisonOriginalCanvas.current, withFindings: false },
        { canvas: comparisonFindingsCanvas.current, withFindings: true },
      ];
      for (const { canvas, withFindings } of canvases) {
        if (!canvas) continue;
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        const context = canvas.getContext('2d');
        if (!context) continue;
        context.drawImage(image, 0, 0);
        if (!withFindings) continue;
        context.strokeStyle = '#f5b544';
        context.lineWidth = Math.max(2, image.naturalWidth / 180);
        for (const region of detectedRegions) {
          const [top, left, bottom, right] = region.bbox;
          if (![top, left, bottom, right].every(Number.isFinite)) continue;
          context.strokeRect(left, top, right - left, bottom - top);
        }
      }
    };
    image.src = url;
    return () => {
      active = false;
      image.onload = null;
      URL.revokeObjectURL(url);
    };
  }, [file, imageAvailable, detectedRegions, mode]);

  const transform = `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`;
  const displayFilter = `contrast(${contrast})`;

  const resetView = () => {
    setZoom(1);
    setContrast(1);
    setOffset({ x: 0, y: 0 });
    setPanEnabled(false);
    setMessage(null);
  };

  const adjustZoom = (delta: number) => {
    setZoom((current) => Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round((current + delta) * 100) / 100)));
  };

  const startPan = (event: PointerEvent<HTMLDivElement>) => {
    if (!panEnabled) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    dragOrigin.current = {
      x: event.clientX,
      y: event.clientY,
      offsetX: offset.x,
      offsetY: offset.y,
    };
  };

  const movePan = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragOrigin.current || !panEnabled) return;
    setOffset({
      x: dragOrigin.current.offsetX + event.clientX - dragOrigin.current.x,
      y: dragOrigin.current.offsetY + event.clientY - dragOrigin.current.y,
    });
  };

  const stopPan = () => {
    dragOrigin.current = null;
  };

  const imageStyle = { transform, filter: displayFilter };
  const unavailable = (details: string) => (
    <div className="image-unavailable">
      <strong>Preview unavailable</strong>
      <p>{details}</p>
    </div>
  );

  const canvasView = (withFindings: boolean, comparison = false) => {
    if (!imageAvailable) {
      return unavailable('This source format cannot be safely rendered in the browser. Use a dedicated DICOM or NIfTI viewer to inspect the original file.');
    }
    const canvas = comparison
      ? withFindings ? comparisonFindingsCanvas : comparisonOriginalCanvas
      : withFindings ? findingsCanvas : originalCanvas;
    return (
      <div
        className={`scan-stage ${panEnabled ? 'panning' : ''}`}
        ref={comparison ? undefined : stage}
        onPointerDown={comparison ? undefined : startPan}
        onPointerMove={comparison ? undefined : movePan}
        onPointerUp={comparison ? undefined : stopPan}
        onPointerCancel={comparison ? undefined : stopPan}
        onLostPointerCapture={comparison ? undefined : stopPan}
        role="group"
        aria-label={panEnabled ? 'Scan image; drag to pan' : 'Scan image preview'}
      >
        <canvas
          ref={canvas}
          style={imageStyle}
          aria-label={withFindings ? 'Scan with heuristic candidate boxes' : 'Original selected scan'}
        />
      </div>
    );
  };

  const renderFindings = () => {
    if (prediction) {
      return (
        <>
          <div
            className={`scan-stage ${panEnabled ? 'panning' : ''}`}
            ref={stage}
            onPointerDown={startPan}
            onPointerMove={movePan}
            onPointerUp={stopPan}
            onPointerCancel={stopPan}
            onLostPointerCapture={stopPan}
            role="group"
            aria-label={panEnabled ? 'Segmentation overlay; drag to pan' : 'Segmentation overlay'}
          >
            <img
              style={imageStyle}
              src={`data:${prediction.overlay_format};base64,${prediction.overlay_png_base64}`}
              alt={`Research binary mask overlay, preview slice ${prediction.preview_slice_index + 1}`}
            />
          </div>
          <p>
            Preview slice {prediction.preview_slice_index + 1} · {prediction.predicted_voxels.toLocaleString()} predicted voxels.
            The overlay is an experimental binary mask, not a tumor diagnosis.
          </p>
          <a
            className="download-mask"
            href={`data:${prediction.mask_format};base64,${prediction.mask_nifti_gz_base64}`}
            download={`mri-${prediction.mask_sha256.slice(0, 12)}-mask.nii.gz`}
          >
            Download NIfTI mask
          </a>
        </>
      );
    }
    return canvasView(true);
  };

  const renderFindingPanel = () => (
    <aside className="finding-panel" aria-label="Analysis findings">
      <h3>AI findings</h3>
      {prediction ? (
        <>
          <p>Research segmentation output · {prediction.target.replaceAll('_', ' ')}. Model output does not establish that an abnormality is present.</p>
          <div className="finding-panel-item">
            <strong>Binary mask</strong>
            <span>{prediction.predicted_voxels.toLocaleString()} voxels</span>
            <small>FLAIR was declared by the uploader and was not verified from image pixels.</small>
          </div>
        </>
      ) : detectedRegions.length ? (
        <>
          <p>Heuristic candidate regions returned by the analysis pipeline. These scores are not medical probabilities.</p>
          <div className="finding-panel-list">
            {detectedRegions.map((region) => (
              <div className="finding-panel-item" key={region.region_id}>
                <strong>Candidate region</strong>
                <span>{region.severity} · heuristic score {(region.confidence * 100).toFixed(0)}%</span>
                <small>
                  {region.slice_index == null ? '2D image' : `Slice ${region.slice_index + 1}`}
                  {' · '}box [{region.bbox.join(', ')}]
                </small>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p>No candidate regions were returned. This does not establish that the scan is normal or exclude disease.</p>
      )}
    </aside>
  );

  const toggleFullscreen = async () => {
    setMessage(null);
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await viewerRoot.current?.requestFullscreen();
      }
    } catch {
      setMessage('Fullscreen is unavailable in this browser context.');
    }
  };

  return (
    <section ref={viewerRoot} className="clinical-viewer viewer-fullscreen" aria-label="MRI image viewer">
      <div className="viewer-toolbar">
        <div className="viewer-tabs" role="tablist" aria-label="Scan views">
          {([
            ['original', 'Original'],
            ['enhanced', 'Enhanced'],
            ['findings', 'AI Findings'],
            ['comparison', 'Comparison'],
          ] as const).map(([value, label]) => (
            <button key={value} type="button" role="tab" aria-selected={mode === value} onClick={() => { setMode(value); setMessage(null); }}>
              {label}
            </button>
          ))}
        </div>
        <div className="viewer-toolbar-actions" aria-label="Image tools">
          <button type="button" onClick={() => adjustZoom(-0.25)} aria-label="Zoom out" title="Zoom out">−</button>
          <button type="button" onClick={() => adjustZoom(0.25)} aria-label="Zoom in" title="Zoom in">＋</button>
          <button type="button" aria-pressed={panEnabled} onClick={() => { setPanEnabled((active) => !active); setMessage(null); }} title="Drag the image to pan">Pan</button>
          <button type="button" onClick={() => setMessage('Calibrated DICOM window/level is not available; this control does not change the source pixels.')} title="Calibrated window/level is unavailable">W/L</button>
          <button type="button" onClick={() => setMessage('Measurement tools are not available in this viewer.')} title="Measurement is unavailable">Measure</button>
          <button type="button" onClick={() => void toggleFullscreen()} aria-label="Toggle fullscreen">⛶</button>
          <button type="button" onClick={resetView}>Reset</button>
        </div>
      </div>

      <div className="viewer-tools">
        <span>{metadata.dimensions.join(' × ')} · {metadata.source_format.toUpperCase()} · {metadata.modality}</span>
        <label>
          Zoom
          <input
            type="range"
            min={MIN_ZOOM}
            max={MAX_ZOOM}
            step="0.1"
            value={zoom}
            onChange={(event) => setZoom(Number(event.target.value))}
            aria-label="Zoom"
          />
          {Math.round(zoom * 100)}%
        </label>
        <label title="Display-only contrast; not calibrated DICOM window/level">
          Display contrast
          <input
            type="range"
            min="0.7"
            max="1.6"
            step="0.05"
            value={contrast}
            onChange={(event) => setContrast(Number(event.target.value))}
            aria-label="Display contrast"
          />
        </label>
      </div>

      {message && <p className="viewer-message" role="status" aria-label="Viewer tool status">{message}</p>}

      {mode === 'original' && canvasView(false)}
      {mode === 'enhanced' && unavailable('The API returns processing metrics but does not return an enhanced image. No transformed image is substituted for the original.')}
      {mode === 'findings' && renderFindings()}
      {mode === 'comparison' && imageAvailable && !prediction ? (
        <div className="comparison-grid">
          <div><strong>Original source</strong>{canvasView(false, true)}</div>
          <div><strong>Heuristic candidate boxes</strong>{canvasView(true, true)}</div>
        </div>
      ) : mode === 'comparison' ? unavailable('A side-by-side comparison is unavailable for this source format or model output.') : null}

      {renderFindingPanel()}

      <div className="viewer-metadata">
        <span>File: {metadata.filename}</span>
        <span>Series navigation: unavailable for this single-file analysis</span>
        {prediction && <span>Preview: axial slice {prediction.preview_slice_index + 1}</span>}
      </div>
    </section>
  );
}
