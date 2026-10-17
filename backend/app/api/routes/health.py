"""Health check routes."""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import logger
from app.schemas.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["Health"])


def _check_database() -> ComponentHealth:
    """Probe the database and return its health.

    Never exposes credentials or raw exception text.
    """
    if not settings.DATABASE_URL:
        return ComponentHealth(status="unavailable", detail="DATABASE_URL not configured")

    try:
        # Import lazily to avoid triggering engine init when DATABASE_URL
        # is not set (Phase 1/2 compatibility).
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return ComponentHealth(status="ok")
        finally:
            db.close()
    except Exception:
        logger.warning("Database health check failed")
        return ComponentHealth(status="unavailable", detail="Cannot reach database")


def create_health_response() -> HealthResponse:
    """Helper to generate a consistent HealthResponse."""
    db_health = _check_database()

    overall = "ok" if db_health.status == "ok" or not settings.DATABASE_URL else "degraded"

    return HealthResponse(
        status=overall,
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        components={"database": db_health},
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the operational status of the service",
)
def get_health() -> HealthResponse:
    """Return current service health."""
    return create_health_response()


@router.get('/ready', include_in_schema=False)
def ready():
    available = _check_database().status == 'ok'
    return JSONResponse({'ready': available}, status_code=200 if available else 503)


@router.get('/metrics', include_in_schema=False, response_class=PlainTextResponse)
def metrics_endpoint():
    from app.core.observability import metrics
    return metrics()
