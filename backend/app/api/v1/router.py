"""Main API v1 router combining sub-routers."""

from fastapi import APIRouter

from backend.app.api.v1.experiments import router as experiments_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.models import router as models_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(models_router)
api_v1_router.include_router(experiments_router)
