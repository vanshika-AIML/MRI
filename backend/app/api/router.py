"""Central API router aggregating all versioned route modules."""
from fastapi import APIRouter
from app.api.routes import analysis, health, auth, annotations

api_router = APIRouter()

# Register route modules
api_router.include_router(health.router)
api_router.include_router(analysis.router)
api_router.include_router(auth.router)
api_router.include_router(annotations.router)
