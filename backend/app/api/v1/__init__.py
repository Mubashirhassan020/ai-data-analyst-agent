from fastapi import APIRouter

from app.api.v1 import ai, analysis, datasets, health, ml, reports

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(datasets.router)
api_router.include_router(analysis.router)
api_router.include_router(ai.router)
api_router.include_router(ml.router)
api_router.include_router(reports.router)
