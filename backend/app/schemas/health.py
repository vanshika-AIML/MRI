"""Health check response schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    """Health status of an individual component."""

    status: str = Field(..., description="ok | unavailable")
    detail: Optional[str] = Field(
        default=None, description="Human-readable note (never credentials)"
    )


class HealthResponse(BaseModel):
    """Predictable response schema for service health checks."""

    status: str = Field(default="ok", description="Operational status of the service")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Current running environment")
    components: Optional[dict[str, ComponentHealth]] = Field(
        default=None,
        description="Optional per-component health breakdown",
    )
