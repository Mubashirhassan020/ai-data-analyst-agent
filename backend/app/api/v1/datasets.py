from __future__ import annotations

import io

from fastapi import APIRouter, File, Query, UploadFile

from app.core.config import get_settings
from app.core.deps import DbSession, StorageDep
from app.core.errors import ValidationError
from app.schemas.chart import EDASuggestionsResponse
from app.schemas.dataset import ColumnDetail, DatasetDetail, DatasetOut
from app.schemas.preview import PreviewPage
from app.schemas.profile import DatasetProfileOut
from app.services.dataset_service import DatasetService
from app.services.profiling_service import ProfilingService
from app.services.visualization_service import VisualizationService

router = APIRouter(prefix="/datasets", tags=["datasets"])

_CHUNK = 1024 * 1024


async def _read_capped(file: UploadFile, limit: int) -> bytes:
    """Read the upload stream but abort as soon as it exceeds `limit` bytes,
    so a mislabeled or oversized upload never gets fully buffered in memory."""
    buf = io.BytesIO()
    total = 0
    while chunk := await file.read(_CHUNK):
        total += len(chunk)
        if total > limit:
            raise ValidationError(
                f"File exceeds max upload size of {limit} bytes.",
                details={"limit": limit},
            )
        buf.write(chunk)
    return buf.getvalue()


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    db: DbSession,
    storage: StorageDep,
    file: UploadFile = File(...),
) -> DatasetOut:
    contents = await _read_capped(file, get_settings().max_upload_size)
    service = DatasetService(db, storage)
    ds = service.ingest(
        filename=file.filename or "upload",
        fileobj=io.BytesIO(contents),
        size=len(contents),
        mime_type=file.content_type,
    )
    return DatasetOut.model_validate(ds)


@router.get("", response_model=list[DatasetOut])
async def list_datasets(db: DbSession, storage: StorageDep) -> list[DatasetOut]:
    service = DatasetService(db, storage)
    return [DatasetOut.model_validate(d) for d in service.list()]


@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(dataset_id: str, db: DbSession, storage: StorageDep) -> DatasetDetail:
    service = DatasetService(db, storage)
    ds = service.get(dataset_id)
    return DatasetDetail.model_validate(ds)


@router.get("/{dataset_id}/preview", response_model=PreviewPage)
async def preview_dataset(
    dataset_id: str,
    db: DbSession,
    storage: StorageDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort: str | None = Query(None),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    search: str | None = Query(None),
) -> PreviewPage:
    service = DatasetService(db, storage)
    result = service.preview(
        dataset_id,
        page=page,
        page_size=page_size,
        sort=sort,
        sort_dir=sort_dir,
        search=search,
    )
    return PreviewPage(**result)


@router.get("/{dataset_id}/profile", response_model=DatasetProfileOut)
async def get_dataset_profile(
    dataset_id: str,
    db: DbSession,
    storage: StorageDep,
    refresh: bool = Query(False, description="Recompute even if a cached profile exists."),
) -> DatasetProfileOut:
    service = ProfilingService(db, storage)
    result = service.get_or_compute(dataset_id, refresh=refresh)
    return DatasetProfileOut(**result)


@router.get("/{dataset_id}/columns", response_model=list[ColumnDetail])
async def get_dataset_columns(dataset_id: str, db: DbSession, storage: StorageDep) -> list[ColumnDetail]:
    service = DatasetService(db, storage)
    ds = service.get(dataset_id)
    return [ColumnDetail.model_validate(c) for c in sorted(ds.columns, key=lambda c: c.position)]


@router.get("/{dataset_id}/eda-suggestions", response_model=EDASuggestionsResponse)
async def get_eda_suggestions(dataset_id: str, db: DbSession, storage: StorageDep) -> EDASuggestionsResponse:
    service = VisualizationService(db, storage)
    result = service.suggest(dataset_id)
    return EDASuggestionsResponse(**result)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, db: DbSession, storage: StorageDep) -> None:
    service = DatasetService(db, storage)
    service.delete(dataset_id)
