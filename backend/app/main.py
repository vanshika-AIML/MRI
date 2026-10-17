"""FastAPI application entrypoint for MRI Analysis System."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.router import api_router
from app.api.routes.health import create_health_response
from app.core.config import settings
from app.core.logging import logger
from app.schemas.health import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management for startup and shutdown."""
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} "
        f"[env: {settings.ENVIRONMENT}, debug: {settings.DEBUG}]"
    )
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


# Initialize FastAPI application with clear metadata
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for AI-Assisted MRI Image Enhancement and Abnormality Detection System.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
from app.core.observability import observe
app.middleware("http")(observe)
from app.core.upload_limit import UploadLimitMiddleware
app.add_middleware(UploadLimitMiddleware)

# Configurable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


# ==============================================================================
# Error Handlers
# ==============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard HTTP exceptions with structured JSON responses."""
    logger.warning(
        f"HTTP {exc.status_code} error on {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {
                "status_code": exc.status_code,
                "message": exc.detail,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors without exposing internal traces."""
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {len(exc.errors())} error(s)"
    )

    def _safe_serialize(val):
        """Recursively make a value JSON-safe.
        Pydantic v2 embeds raw Exception objects in error ctx dicts which
        Python's json.dumps cannot serialize.
        """
        if isinstance(val, dict):
            return {k: _safe_serialize(v) for k, v in val.items()}
        if isinstance(val, (list, tuple)):
            return [_safe_serialize(v) for v in val]
        if isinstance(val, Exception):
            return str(val)
        if not isinstance(val, (str, int, float, bool, type(None))):
            return str(val)
        return val

    safe_errors = [_safe_serialize({k: v for k, v in e.items() if k not in {"input", "ctx"}}) for e in exc.errors()]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "status_code": 422,
                "message": "Request validation failed",
                "details": safe_errors,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled server exceptions."""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=settings.DEBUG,
    )
    message = str(exc) if settings.DEBUG else "An internal server error occurred."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "status_code": 500,
                "message": message,
            }
        },
    )


# ==============================================================================
# Router Registrations
# ==============================================================================

# Central versioned API router: /api/v1/...
app.include_router(api_router, prefix=settings.API_PREFIX)


# Backward-compatible root /health endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Root Health Check",
    description="Operational status of the service (backward compatibility with Phase 1)",
    tags=["Health"],
)
def root_health() -> HealthResponse:
    """Return health status at root level."""
    return create_health_response()


# Informational root endpoint
@app.get("/", tags=["System"], summary="API Root Information")
def root_info():
    """Service info and links to documentation and health endpoints."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api_v1_health": f"{settings.API_PREFIX}/health",
    }
