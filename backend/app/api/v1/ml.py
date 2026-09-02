from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import DbSession, StorageDep
from app.schemas.ml import MLModelOut, MLSuggestionsResponse, MLSuggestRequest, MLTrainRequest
from app.services.ml_service import MLService

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/suggest", response_model=MLSuggestionsResponse)
async def suggest_ml_tasks(payload: MLSuggestRequest, db: DbSession, storage: StorageDep) -> MLSuggestionsResponse:
    service = MLService(db, storage)
    result = service.suggest(payload.dataset_id)
    return MLSuggestionsResponse(**result)


@router.post("/train", response_model=MLModelOut)
async def train_model(payload: MLTrainRequest, db: DbSession, storage: StorageDep) -> MLModelOut:
    service = MLService(db, storage)
    result = service.train(payload)
    return MLModelOut(**result)


@router.get("/{model_id}/results", response_model=MLModelOut)
async def get_model_results(model_id: str, db: DbSession, storage: StorageDep) -> MLModelOut:
    service = MLService(db, storage)
    result = service.get_model(model_id)
    return MLModelOut(**result)
