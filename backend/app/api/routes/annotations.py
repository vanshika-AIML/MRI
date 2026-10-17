"""Analysis annotation routes — Phase 9.

Provides user-controlled annotation of analysis reports.
Separates model-generated findings from user annotations.
"""

from typing import List, Optional
from app.services.reports import require_report

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    AuditLogger,
    get_audit_logger,
    get_current_user,
    get_db_optional,
)
from app.models.annotation import AnalysisAnnotation
from app.schemas.annotation import (
    AnnotationCreateRequest,
    AnnotationResponse,
    AnnotationUpdateRequest,
)

router = APIRouter(prefix="/analysis", tags=["Annotations"])

_ALLOWED_ROLES_ANNOTATE = {"radiologist", "admin"}


def _require_annotate_role(current_user: dict) -> None:
    """Require radiologist or admin role for annotation creation/modification."""
    if current_user.get("role") not in _ALLOWED_ROLES_ANNOTATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Annotation requires 'radiologist' or 'admin' role. "
                f"Your role: {current_user.get('role', 'unknown')}."
            ),
        )


def _to_response(ann: AnalysisAnnotation) -> AnnotationResponse:
    return AnnotationResponse(
        id=str(ann.id),
        analysis_id=ann.analysis_id,
        user_id=str(ann.user_id),
        annotation_text=ann.annotation_text,
        field_name=ann.field_name,
        is_original=ann.is_original,
        version=ann.version,
        created_at=ann.created_at.isoformat() if ann.created_at else "",
    )


# ==============================================================================
# List annotations for an analysis
# ==============================================================================

@router.get(
    "/{analysis_id}/annotations",
    response_model=List[AnnotationResponse],
    summary="List annotations for an analysis",
    description=(
        "Returns all user annotations for the given analysis ID. "
        "Requires authentication. All authenticated users can read annotations."
    ),
    responses={
        200: {"description": "Annotations returned"},
        401: {"description": "Authentication required"},
        503: {"description": "Database unavailable"},
    },
)
async def list_annotations(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
    db: Optional[Session] = Depends(get_db_optional),
):
    """List all annotations for the given analysis."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    require_report(db, analysis_id, current_user)
    annotations = db.execute(
        select(AnalysisAnnotation)
        .where(AnalysisAnnotation.analysis_id == analysis_id)
        .order_by(AnalysisAnnotation.created_at.asc())
    ).scalars().all()

    return [_to_response(ann) for ann in annotations]


# ==============================================================================
# Create annotation
# ==============================================================================

@router.post(
    "/{analysis_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user annotation to an analysis",
    description=(
        "Attach a text annotation to an analysis result. "
        "Requires 'radiologist' or 'admin' role. "
        "Annotations are clearly distinguished from model-generated findings."
    ),
    responses={
        201: {"description": "Annotation created"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient role"},
        503: {"description": "Database unavailable"},
    },
)
async def create_annotation(
    analysis_id: str,
    data: AnnotationCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Optional[Session] = Depends(get_db_optional),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Create a user annotation on an analysis."""
    _require_annotate_role(current_user)

    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    require_report(db, analysis_id, current_user)
    import uuid
    annotation = AnalysisAnnotation(
        analysis_id=analysis_id,
        user_id=uuid.UUID(current_user["sub"]),
        annotation_text=data.annotation_text,
        field_name=data.field_name,
        is_original=False,  # User annotations are NEVER marked as original
        version=1,
    )
    db.add(annotation)
    db.flush()

    audit.log(
        action="analysis.annotation_create",
        user_id=current_user["sub"],
        resource_type="annotation",
        resource_id=str(annotation.id),
        outcome="success",
        details={"analysis_id": analysis_id, "field_name": data.field_name},
    )

    return _to_response(annotation)


# ==============================================================================
# Update annotation (own annotations only, or admin)
# ==============================================================================

@router.patch(
    "/{analysis_id}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
    summary="Update an annotation",
    description=(
        "Update your own annotation text. "
        "Creates a new version record; the original is preserved as superseded. "
        "Admins can update any annotation."
    ),
    responses={
        200: {"description": "Annotation updated"},
        401: {"description": "Authentication required"},
        403: {"description": "Cannot modify another user's annotation"},
        404: {"description": "Annotation not found"},
        503: {"description": "Database unavailable"},
    },
)
async def update_annotation(
    analysis_id: str,
    annotation_id: str,
    data: AnnotationUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Optional[Session] = Depends(get_db_optional),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Update an existing annotation."""
    _require_annotate_role(current_user)

    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        )

    require_report(db, analysis_id, current_user)
    import uuid
    try:
        ann_uuid = uuid.UUID(annotation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid annotation ID format.",
        )

    existing = db.execute(
        select(AnalysisAnnotation).where(
            AnalysisAnnotation.id == ann_uuid,
            AnalysisAnnotation.analysis_id == analysis_id,
        )
    ).scalar_one_or_none()

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found.",
        )

    # Ownership check — admins can edit any annotation
    if (str(existing.user_id) != current_user["sub"]
            and current_user.get("role") != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own annotations.",
        )

    # Preserve provenance: create new version, mark old as superseded
    new_annotation = AnalysisAnnotation(
        analysis_id=analysis_id,
        user_id=uuid.UUID(current_user["sub"]),
        annotation_text=data.annotation_text,
        field_name=existing.field_name,
        is_original=False,
        version=existing.version + 1,
        superseded_by_id=None,
    )
    db.add(new_annotation)
    db.flush()

    # Mark old as superseded
    existing.superseded_by_id = new_annotation.id
    db.flush()

    audit.log(
        action="analysis.annotation_update",
        user_id=current_user["sub"],
        resource_type="annotation",
        resource_id=str(new_annotation.id),
        outcome="success",
        details={
            "analysis_id": analysis_id,
            "previous_annotation_id": str(existing.id),
            "new_version": new_annotation.version,
        },
    )

    return _to_response(new_annotation)
