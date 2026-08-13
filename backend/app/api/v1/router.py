"""Main API v1 router combining sub-routers."""

from fastapi import APIRouter

from backend.app.api.v1.agent import router as agent_router
from backend.app.api.v1.benchmarks import router as benchmarks_router
from backend.app.api.v1.deployment import router as deployment_router
from backend.app.api.v1.experiments import router as experiments_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.models import router as models_router
from backend.app.api.v1.openai_api import router as openai_router
from backend.app.api.v1.optimization import router as optimization_router
from backend.app.api.v1.operational import router as operational_router
from backend.app.api.v1.performix import router as performix_router
from backend.app.api.v1.quality import router as quality_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(models_router)
api_v1_router.include_router(experiments_router)
api_v1_router.include_router(openai_router)
api_v1_router.include_router(benchmarks_router)
api_v1_router.include_router(optimization_router)
api_v1_router.include_router(quality_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(deployment_router)
api_v1_router.include_router(performix_router)
api_v1_router.include_router(operational_router)


