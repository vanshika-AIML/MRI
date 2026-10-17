"""Annotation Pydantic schemas for report modification API."""
from typing import Optional
from pydantic import BaseModel, Field


class AnnotationCreateRequest(BaseModel):
    """Schema for POST /api/v1/analysis/{analysis_id}/annotations."""

    annotation_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User annotation text (max 5000 characters)",
    )
    field_name: Optional[str] = Field(
        None,
        max_length=128,
        description="Optional field being annotated (e.g. 'summary', 'severity_note')",
    )


class AnnotationResponse(BaseModel):
    """Public annotation response schema."""

    id: str = Field(..., description="Annotation UUID")
    analysis_id: str = Field(..., description="Analysis ID this annotation belongs to")
    user_id: str = Field(..., description="Author user UUID")
    annotation_text: str = Field(..., description="Annotation content")
    field_name: Optional[str] = Field(None, description="Optional field name")
    is_original: bool = Field(..., description="True only for model-generated entries")
    version: int = Field(..., description="Edit version number")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")

    model_config = {"from_attributes": True}


class AnnotationUpdateRequest(BaseModel):
    """Schema for PATCH /api/v1/analysis/{analysis_id}/annotations/{annotation_id}."""

    annotation_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Updated annotation text",
    )
