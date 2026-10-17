"""Analysis Service for MRI AI Inference (Phase 6).

Serves as the bridge between FastAPI route handlers and the ML inference pipeline
(ml.inference.pipeline.MRIInferencePipeline).

Handles file ingestion/decoding, input validation, execution of preprocessing,
enhancement, and abnormality detection pipelines via ModelRegistry, formatting
API responses, and persisting DB analysis entities when PostgreSQL is active.
"""

import logging
from pathlib import Path
import tempfile
import io
import zipfile
import gzip
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import numpy as np
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from ml.inference.pipeline import MRIInferencePipeline
from ml.inference.schemas import InferenceInput
from ml.models.registry import ModelRegistry
from ml.preprocessing.dicom_reader import DICOMReader
from ml.preprocessing.nifti_reader import NIfTIReader

from app.schemas.analysis import (
    CLINICAL_DISCLAIMER,
    AnalysisOptions,
    AnalysisResponse,
    DetectedRegionSchema,
    InputMetadataSchema,
    StageResultSchema,
)

logger = logging.getLogger(__name__)

MAX_VOXELS = 16_777_216
MAX_DECODED_BYTES = 128 * 1024 * 1024

def _check_npy_header(stream):
    version = np.lib.format.read_magic(stream)
    reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
    shape, _, dtype = reader(stream)
    if dtype.hasobject or dtype.kind not in "buif" or math.prod(shape) > MAX_VOXELS or math.prod(shape) * dtype.itemsize > MAX_DECODED_BYTES:
        raise ValueError("MRI array exceeds decoded limits or has unsupported dtype")


MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB maximum upload size limit


class AnalysisService:
    """Domain service orchestrating MRI file parsing, validation, and AI inference."""

    def __init__(
        self,
        db: Optional[Session] = None,
        registry: Optional[ModelRegistry] = None,
    ):
        self.db = db
        self.registry = registry or ModelRegistry.create_default()
        self.pipeline = MRIInferencePipeline(registry=self.registry)

    def parse_and_validate_file(
        self,
        file_bytes: bytes,
        original_filename: str,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Parse raw file bytes, validate input array, and extract metadata.

        Supports DICOM (.dcm), NIfTI (.nii, .nii.gz), Image (.png, .jpg, .jpeg, .tiff, .bmp),
        and Numpy (.npy, .npz) formats.
        """
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty (0 bytes)")

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError("Uploaded file exceeds maximum size limit of 100MB")

        safe_filename = Path((original_filename or "uploaded_mri").replace("\\", "/")).name[:200]
        ext_lower = safe_filename.lower()

        if ext_lower.endswith('.npy'):
            _check_npy_header(io.BytesIO(file_bytes))
        elif ext_lower.endswith('.npz'):
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                entries = archive.infolist()
                if not entries or sum(e.file_size for e in entries) > MAX_DECODED_BYTES:
                    raise ValueError("NumPy archive exceeds decoded limits or is empty")
                for entry in entries:
                    with archive.open(entry) as stream:
                        _check_npy_header(stream)
        elif ext_lower.endswith('.nii.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(file_bytes)) as stream:
                if len(stream.read(MAX_DECODED_BYTES + 1)) > MAX_DECODED_BYTES:
                    raise ValueError("NIfTI exceeds decoded limits")
        # Write to temporary file for format parsers
        with tempfile.NamedTemporaryFile(suffix=".nii.gz" if ext_lower.endswith(".nii.gz") else Path(safe_filename).suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            arr: Optional[np.ndarray] = None
            metadata: Dict[str, Any] = {
                "filename": safe_filename,
                "modality": "MR",
            }

            if ext_lower.endswith(".dcm") or ext_lower.endswith(".dicom"):
                metadata["source_format"] = "dicom"
                try:
                    reader = DICOMReader(tmp_path)
                    dataset = reader.read()
                    frames = int(getattr(dataset, "NumberOfFrames", 1))
                    if int(getattr(dataset, "SamplesPerPixel", 1)) != 1:
                        raise ValueError("Only grayscale DICOM is supported")
                    if frames < 1 or int(dataset.Rows) * int(dataset.Columns) * frames > MAX_VOXELS:
                        raise ValueError("DICOM exceeds voxel limit")
                    dcm_meta = reader.extract_metadata()
                    metadata.update({
                        "patient_id": dcm_meta.patient_id,
                        "study_instance_uid": dcm_meta.study_instance_uid,
                        "series_instance_uid": dcm_meta.series_instance_uid,
                        "modality": dcm_meta.modality or "MR",
                    })
                    arr = reader.get_pixel_array(apply_rescale=True)
                    if frames > 1:
                        # pydicom returns F,H,W; the pipeline expects H,W,D.
                        arr = np.moveaxis(arr, 0, -1)
                except Exception as e:
                    raise ValueError("Corrupt or invalid DICOM file")

            elif ext_lower.endswith(".nii") or ext_lower.endswith(".nii.gz"):
                metadata["source_format"] = "nifti"
                try:
                    reader = NIfTIReader(tmp_path)
                    nii_meta = reader.extract_metadata()
                    metadata.update({
                        "dimensions": nii_meta.dimensions,
                    })
                    if math.prod(nii_meta.dimensions) > MAX_VOXELS:
                        raise ValueError("NIfTI exceeds voxel limit")
                    arr = reader.get_fdata()
                except Exception as e:
                    raise ValueError("Corrupt or invalid NIfTI file")

            elif any(ext_lower.endswith(img_ext) for img_ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]):
                metadata["source_format"] = "image"
                try:
                    with PILImage.open(tmp_path) as img:
                        if img.width * img.height > MAX_VOXELS:
                            raise ValueError("Image exceeds pixel limit")
                        gray_img = img.convert("L")
                        arr = np.array(gray_img, dtype=np.float32)
                except Exception as e:
                    raise ValueError("Corrupt or invalid image file")

            elif ext_lower.endswith(".npy") or ext_lower.endswith(".npz"):
                metadata["source_format"] = "numpy"
                try:
                    loaded = np.load(tmp_path, allow_pickle=False)
                    if isinstance(loaded, np.lib.npyio.NpzFile):
                        with loaded:
                            first_key = loaded.files[0]
                            arr = loaded[first_key]
                    else:
                        arr = loaded
                    arr = arr.astype(np.float32)
                except Exception as e:
                    raise ValueError("Corrupt or invalid NumPy data file")

            else:
                # Try image format fallback, or raise unsupported
                try:
                    with PILImage.open(tmp_path) as img:
                        if img.width * img.height > MAX_VOXELS:
                            raise ValueError("Image exceeds pixel limit")
                        gray_img = img.convert("L")
                        arr = np.array(gray_img, dtype=np.float32)
                        metadata["source_format"] = "image"
                except Exception:
                    raise ValueError(
                        f"Unsupported MRI file format: '{safe_filename}'. "
                        "Supported extensions: .dcm, .nii, .nii.gz, .png, .jpg, .jpeg, .npy, .npz"
                    )

            if arr is None or not isinstance(arr, np.ndarray):
                raise ValueError("Failed to extract array from uploaded MRI file")

            # Strictly validate array shape, dimensionality, and numeric content
            if arr.size > MAX_VOXELS:
                raise ValueError("MRI exceeds voxel limit")
            if arr.size == 0:
                raise ValueError("Extracted MRI array is empty (0 elements)")

            if arr.ndim not in (2, 3):
                raise ValueError(
                    f"Unsupported MRI array dimension: {arr.ndim}D with shape {arr.shape}. "
                    "Only 2D slices (H, W) or 3D volumes (H, W, D) are supported."
                )

            if not np.issubdtype(arr.dtype, np.number) or np.isnan(arr).any() or np.isinf(arr).any():
                raise ValueError("MRI array contains non-numeric, NaN, or infinite voxel values")

            return arr, metadata

        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception as cleanup_err:
                    logger.warning(f"Failed to remove temporary file {tmp_path}: {cleanup_err}")

    def run_analysis(
        self,
        image_array: np.ndarray,
        file_meta: Dict[str, Any],
        options: Optional[AnalysisOptions] = None,
    ) -> AnalysisResponse:
        """Execute AI inference pipeline and return typed API response."""
        if options is None:
            options = AnalysisOptions()

        inf_input = InferenceInput(
            image_id=file_meta.get("filename"),
            source_format=file_meta.get("source_format"),
            modality=file_meta.get("modality", "MR"),
            normalize=options.normalize,
            normalization_method=options.normalization_method,
            enable_enhancement=options.enable_enhancement,
            enhancement_methods=options.enhancement_methods,
            enable_detection=options.enable_detection,
            detection_methods=options.detection_methods,
            detection_confidence_threshold=options.confidence_threshold,
        )

        pipeline_output = self.pipeline.run(image_array, config=inf_input)

        # Stage results mapping
        stage_results = [
            StageResultSchema(
                stage=sr.stage.value if hasattr(sr.stage, "value") else str(sr.stage),
                success=sr.success,
                duration_ms=sr.duration_ms,
                details=sr.details,
                error_message=sr.error_message,
            )
            for sr in pipeline_output.stage_results
        ]

        # Extract detected regions
        detected_regions: List[DetectedRegionSchema] = []
        region_count = 0
        peak_confidence = 0.0
        severity_rank = {"none": 0, "low": 1, "moderate": 2, "medium": 2, "high": 3}
        highest_severity_score = 0
        severity_label = "not_assessed"

        for det_res in pipeline_output.detection_results:
            for reg in det_res.regions:
                region_count += 1
                conf = float(reg.confidence)
                if conf > peak_confidence:
                    peak_confidence = conf

                reg_sev = str(reg.severity.value if hasattr(reg.severity, "value") else reg.severity).lower()
                sev_val = severity_rank.get(reg_sev, 1)
                if sev_val > highest_severity_score:
                    highest_severity_score = sev_val
                    severity_label = "medium" if reg_sev == "moderate" else reg_sev

                bbox_list = list(reg.bounding_box) if reg.bounding_box else [0, 0, 0, 0]
                centroid_list = list(reg.centroid) if reg.centroid else [0.0, 0.0]
                slice_idx = reg.metadata.get("slice_index") if reg.metadata else None

                detected_regions.append(
                    DetectedRegionSchema(
                        region_id=reg.region_id,
                        bbox=bbox_list,
                        centroid=centroid_list,
                        area_pixels=reg.area_pixels or 0,
                        mean_intensity=float(reg.mean_intensity or 0.0),
                        max_intensity=float(reg.metadata.get("max_intensity", reg.mean_intensity or 0.0)),
                        anomaly_score=float(reg.metadata.get("anomaly_score", reg.confidence)),
                        confidence=conf,
                        severity="medium" if reg_sev == "moderate" else reg_sev,
                        slice_index=slice_idx,
                    )
                )

        input_meta_schema = InputMetadataSchema(
            filename=file_meta.get("filename", "uploaded_mri"),
            source_format=file_meta.get("source_format", "unknown"),
            dimensions=list(pipeline_output.input_shape),
            ndim=len(pipeline_output.input_shape),
            modality=file_meta.get("modality", "MR"),
            patient_id=file_meta.get("patient_id"),
            study_instance_uid=file_meta.get("study_instance_uid"),
            series_instance_uid=file_meta.get("series_instance_uid"),
        )

        analysis_id = uuid.uuid4().hex

        response = AnalysisResponse(
            analysis_id=analysis_id,
            status="completed" if pipeline_output.success else "failed",
            success=pipeline_output.success,
            input_metadata=input_meta_schema,
            model_name="baseline_mri_pipeline",
            model_version="1.0.0",
            is_baseline=pipeline_output.is_baseline,
            total_duration_ms=pipeline_output.total_duration_ms,
            severity=severity_label,
            overall_confidence=round(peak_confidence, 4),
            detected_regions_count=region_count,
            detected_regions=detected_regions,
            stage_results=stage_results,
            summary=pipeline_output.summary,
            warnings=(
                [
                    "No candidate regions were returned by the baseline heuristic. "
                    "This result cannot establish that the scan is normal."
                ]
                if region_count == 0
                else []
            ),
            error_message=pipeline_output.error_message,
            clinical_disclaimer=CLINICAL_DISCLAIMER,
        )

        # Persistence to DB when available
        if self.db is not None and options.study_id:
            self._persist_analysis_record(response, options)

        return response

    def _persist_analysis_record(
        self,
        response: AnalysisResponse,
        options: AnalysisOptions,
    ) -> None:
        """Persist analysis result entity to database if available."""
        from app.repositories.analysis import AnalysisRepository
        with self.db.begin_nested():
            AnalysisRepository(self.db).create(
                id=uuid.UUID(response.analysis_id),
                study_id=uuid.UUID(options.study_id),
                analysis_type="abnormality_detection",
                model_name=response.model_name, model_version=response.model_version,
                status=response.status, result=response.model_dump(),
                confidence=response.overall_confidence)
