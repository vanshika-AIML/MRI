"""MRI AI Inference API Route Handler (Phase 6).

Exposes POST /api/v1/analysis for client application file uploads and pipeline execution.
"""

import asyncio
import logging
import time
import uuid
from typing import Optional
from fastapi import Request
from app.core.rate_limit import limiter
from app.core.config import settings
from starlette.concurrency import run_in_threadpool
from app.models.report import AnalysisReport
from app.services.reports import require_report
from app.api.dependencies import get_current_user
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import get_db_optional, get_current_user_optional, verify_auth_header
from app.schemas.analysis import (
    CLINICAL_DISCLAIMER,
    AnalysisOptions,
    AnalysisResponse,
    InputMetadataSchema,
    StageResultSchema,
)
from app.services.analysis import AnalysisService, MAX_FILE_SIZE_BYTES
from app.services.tumor_segmentation import (
    TumorModelConfigurationError,
    get_tumor_segmenter,
)

router = APIRouter(tags=["Analysis"])
logger = logging.getLogger(__name__)
_RESEARCH_INFERENCE_GATE = asyncio.Semaphore(1)


@router.get("/analysis/reports")
def list_owned_reports(
    current_user: dict = Depends(get_current_user),
    db: Optional[Session] = Depends(get_db_optional),
):
    """Recent reports owned by this account, without embedded images or masks."""
    if db is None:
        raise HTTPException(503, "Database unavailable.")
    try:
        owner_id = uuid.UUID(current_user["sub"])
    except (KeyError, ValueError):
        raise HTTPException(401, "Valid account required.")
    rows = db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.owner_id == owner_id)
        .order_by(AnalysisReport.created_at.desc())
        .limit(50)
    ).scalars().all()
    return [
        {
            "analysis_id": row.result.get("analysis_id", str(row.id)),
            "timestamp": row.result.get("timestamp") or row.created_at.isoformat(),
            "filename": row.result.get("input_metadata", {}).get("filename", "Scan"),
            "patient_id": row.result.get("input_metadata", {}).get("patient_id"),
            "model_name": row.result.get("model_name", "Unknown"),
            "is_baseline": bool(row.result.get("is_baseline", True)),
            "success": bool(row.result.get("success", False)),
            "status": row.result.get("status", "unknown"),
            "has_prediction": row.result.get("prediction") is not None,
        }
        for row in rows
    ]


async def _run_research_segmentation(
    file: UploadFile,
    db: Session,
    owner_id: uuid.UUID,
) -> AnalysisResponse:
    async with _RESEARCH_INFERENCE_GATE:
        try:
            content = await file.read(MAX_FILE_SIZE_BYTES + 1)
        except Exception:
            logger.exception("Failed to read uploaded research FLAIR volume")
            raise HTTPException(400, "Failed to read uploaded NIfTI file.")
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(413, "Uploaded file exceeds maximum size limit of 100MB")

        supplied_filename = (file.filename or "").lower()
        filename = (
            "research_flair.nii.gz"
            if supplied_filename.endswith(".nii.gz")
            else "research_flair.nii"
            if supplied_filename.endswith(".nii")
            else "unsupported_upload"
        )
        started = time.perf_counter()
        try:
            segmenter = get_tumor_segmenter()
            prediction = await run_in_threadpool(segmenter.predict, content, filename)
        except FileNotFoundError as err:
            logger.warning("Research segmentation model is unavailable: %s", err)
            raise HTTPException(503, "Research segmentation model is not configured or available.")
        except ImportError:
            logger.exception("Research segmentation runtime dependencies are unavailable")
            raise HTTPException(503, "Research segmentation runtime dependencies are unavailable.")
        except TumorModelConfigurationError:
            logger.exception("Configured research segmentation model is invalid")
            raise HTTPException(503, "Configured research segmentation model is invalid or incompatible.")
        except ValueError as err:
            raise HTTPException(400, str(err))
        except Exception:
            logger.exception("Research FLAIR segmentation inference failed")
            raise HTTPException(500, "Research segmentation inference failed; no baseline fallback was run.")

        duration_ms = (time.perf_counter() - started) * 1000
        response = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            input_metadata=InputMetadataSchema(
                filename=filename,
                source_format="nifti",
                dimensions=prediction["mask_dimensions"],
                ndim=3,
                modality="FLAIR",
                sequence_confirmed_by_user=True,
            ),
            model_name="msd_flair_whole_tumor_unet",
            model_version=prediction["checkpoint_sha256"][:16],
            is_baseline=False,
            total_duration_ms=duration_ms,
            severity="not_assessed",
            overall_confidence=0.0,
            detected_regions_count=0,
            detected_regions=[],
            prediction=prediction,
            stage_results=[
                StageResultSchema(
                    stage="research_flair_segmentation",
                    success=True,
                    duration_ms=duration_ms,
                    details={
                        "target": prediction["target"],
                        "predicted_voxels": prediction["predicted_voxels"],
                        "checkpoint_sha256": prediction["checkpoint_sha256"],
                        "preprocessing_version": prediction["preprocessing_version"],
                    },
                )
            ],
            summary=(
                "Experimental whole-tumor segmentation mask generated for research review. "
                "This output does not establish tumor presence or a clinical diagnosis."
            ),
            warnings=[
                "Research-only model; not clinically validated or intended to guide patient care.",
                "FLAIR sequence and brain anatomy were declared by the uploader and are not independently verified from NIfTI voxel data.",
            ],
            clinical_disclaimer=CLINICAL_DISCLAIMER,
        )
        try:
            db.add(
                AnalysisReport(
                    id=uuid.UUID(response.analysis_id),
                    owner_id=owner_id,
                    result=response.model_dump(),
                )
            )
            db.flush()
        except Exception:
            logger.exception("Failed to persist research segmentation report")
            raise HTTPException(500, "Research segmentation report could not be saved.")
        return response


@router.post(
    "/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run AI Inference Pipeline on Uploaded MRI",
    description=(
        "Upload an MRI image or volume and select the baseline heuristic workflow or the opt-in "
        "research FLAIR whole-tumor segmentation workflow. Research segmentation accepts only NIfTI "
        "FLAIR volumes and requires authentication, a reachable database, and a configured local model run. "
        "It returns a geometry-preserving NIfTI mask, preview overlay and checkpoint/input provenance. "
        "The research model never falls back to heuristics.\n\n"
        "All outputs are experimental and are not clinical probabilities, diagnoses, or medical advice."
    ),
    responses={
        200: {"description": "Inference completed successfully"},
        400: {"description": "Invalid, corrupt, empty, or unsupported MRI input file"},
        413: {"description": "Uploaded file exceeds maximum size limit (100MB)"},
        422: {"description": "Form validation failure"},
        500: {"description": "Internal server processing error"},
    },
)
@limiter.limit(settings.RATE_LIMIT_ANALYSIS)
async def run_mri_analysis(
    request: Request,
    file: UploadFile = File(
        ...,
        description="Uploaded MRI image or 3D volume file (.dcm, .nii, .nii.gz, .png, .jpg, .jpeg, .npy)",
    ),
    normalize: bool = Form(True, description="Apply intensity normalization"),
    normalization_method: str = Form("minmax", description="Normalization algorithm: minmax or zscore"),
    enable_enhancement: bool = Form(True, description="Enable image enhancement stage"),
    enhancement_methods: Optional[str] = Form(
        None,
        description="Comma-separated enhancement methods (e.g. 'clahe,gaussian')",
    ),
    enable_detection: bool = Form(True, description="Enable abnormality detection stage"),
    detection_methods: Optional[str] = Form(
        None,
        description="Comma-separated detection methods (e.g. 'intensity_anomaly,texture_anomaly')",
    ),
    confidence_threshold: float = Form(
        0.3, ge=0.0, le=1.0, description="Minimum confidence threshold for detected regions"
    ),
    study_id: Optional[str] = Form(None, description="Optional associated study UUID"),
    analysis_method: str = Form(
        "baseline",
        description="Analysis mode: baseline or research_flair_segmentation",
    ),
    flair_sequence_confirmed: bool = Form(
        False,
        description="Uploader confirms the research input is a brain FLAIR NIfTI volume",
    ),
    db: Optional[Session] = Depends(get_db_optional),
    auth_header: Optional[str] = Depends(verify_auth_header),
    current_user: Optional[dict] = Depends(get_current_user_optional),
) -> AnalysisResponse:
    """Execute end-to-end AI analysis on an uploaded MRI image or volume."""
    if current_user is None:
        raise HTTPException(401, "Authentication is required to analyze MRI uploads.")
    if analysis_method not in ("baseline", "research_flair_segmentation"):
        raise HTTPException(400, "Unsupported analysis method.")
    segmentation_owner_id: Optional[uuid.UUID] = None
    if analysis_method == "research_flair_segmentation":
        if current_user is None:
            raise HTTPException(401, "Authentication is required for research segmentation.")
        if not flair_sequence_confirmed:
            raise HTTPException(
                400,
                "Research segmentation requires confirmation that the NIfTI is a brain FLAIR volume.",
            )
        try:
            segmentation_owner_id = uuid.UUID(current_user["sub"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(401, "A valid authenticated account is required for research segmentation.")
        if db is None:
            raise HTTPException(503, "Database is required to save research segmentation reports.")
    if study_id:
        if current_user is None or current_user.get("role") != "admin":
            raise HTTPException(403, "Clinical study linkage requires an administrator.")
        if db is None:
            raise HTTPException(503, "Database unavailable.")
        from app.models.study import Study
        try:
            study = db.get(Study, uuid.UUID(study_id))
        except ValueError:
            study = None
        if study is None:
            raise HTTPException(404, "Study not found.")
    # Parse enhancement and detection method lists if provided as strings
    enh_list = (
        [m.strip() for m in enhancement_methods.split(",") if m.strip()]
        if enhancement_methods
        else ["clahe"]
    )
    det_list = (
        [m.strip() for m in detection_methods.split(",") if m.strip()]
        if detection_methods
        else ["intensity_anomaly"]
    )

    options = AnalysisOptions(
        normalize=normalize,
        normalization_method=normalization_method,
        enable_enhancement=enable_enhancement,
        enhancement_methods=enh_list,
        enable_detection=enable_detection,
        detection_methods=det_list,
        confidence_threshold=confidence_threshold,
        study_id=study_id,
    )

    if analysis_method == "research_flair_segmentation":
        return await _run_research_segmentation(file, db, segmentation_owner_id)

    try:
        content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    except Exception as read_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file stream: {read_err}",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(413, "Uploaded file exceeds maximum size limit of 100MB")

    service = AnalysisService(db=db)

    try:
        image_array, file_meta = await run_in_threadpool(service.parse_and_validate_file,
            file_bytes=content,
            original_filename=file.filename or "uploaded_mri",
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if "exceeds maximum size" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except Exception as parse_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupt MRI file.",
        )

    try:
        response = await run_in_threadpool(service.run_analysis,
            image_array=image_array,
            file_meta=file_meta,
            options=options,
        )
        if db is not None and current_user is not None:
            db.add(AnalysisReport(id=uuid.UUID(response.analysis_id), owner_id=uuid.UUID(current_user["sub"]), result=response.model_dump()))
            db.flush()
        return response
    except Exception as pipeline_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during MRI analysis.",
        )


@router.get("/analysis/{analysis_id}/report", response_model=AnalysisResponse)
def get_report(analysis_id: str, current_user: dict = Depends(get_current_user), db=Depends(get_db_optional)):
    return require_report(db, analysis_id, current_user).result
