from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import DbSession, StorageDep
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResultOut,
    AnalysisResultSummary,
    AnalysisSessionOut,
    CorrelationRequest,
    CorrelationResult,
    ForecastRequest,
    ForecastResult,
    OutlierRequest,
    OutlierResult,
    SqlRequest,
    SqlResult,
)
from app.schemas.chart import ChartRequest, ChartResult
from app.services.analytics_service import AnalyticsService
from app.services.visualization_service import VisualizationService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/execute", response_model=AnalysisResultOut)
async def execute_analysis(payload: AnalysisRequest, db: DbSession, storage: StorageDep) -> AnalysisResultOut:
    service = AnalyticsService(db, storage)
    result = service.execute(payload)
    return AnalysisResultOut(**result)


@router.post("/correlation", response_model=CorrelationResult)
async def correlation(payload: CorrelationRequest, db: DbSession, storage: StorageDep) -> CorrelationResult:
    service = AnalyticsService(db, storage)
    return CorrelationResult(**service.correlation(payload))


@router.post("/outliers", response_model=OutlierResult)
async def outliers(payload: OutlierRequest, db: DbSession, storage: StorageDep) -> OutlierResult:
    service = AnalyticsService(db, storage)
    return OutlierResult(**service.outliers(payload))


@router.post("/sql", response_model=SqlResult)
async def run_sql(payload: SqlRequest, db: DbSession, storage: StorageDep) -> SqlResult:
    service = AnalyticsService(db, storage)
    result = service.sql(payload)
    return SqlResult(**result)


@router.post("/forecast", response_model=ForecastResult)
async def run_forecast(payload: ForecastRequest, db: DbSession, storage: StorageDep) -> ForecastResult:
    service = AnalyticsService(db, storage)
    result = service.forecast(payload)
    return ForecastResult(**result)


@router.post("/chart", response_model=ChartResult)
async def build_chart(payload: ChartRequest, db: DbSession, storage: StorageDep) -> ChartResult:
    service = VisualizationService(db, storage)
    result = service.build(payload)
    return ChartResult(**result)


@router.get("/sessions/{session_id}", response_model=AnalysisSessionOut)
async def get_session(session_id: str, db: DbSession, storage: StorageDep) -> AnalysisSessionOut:
    service = AnalyticsService(db, storage)
    session = service.get_session(session_id)
    return AnalysisSessionOut(
        id=session.id,
        dataset_id=session.dataset_id,
        title=session.title,
        created_at=session.created_at,
        results=[
            AnalysisResultSummary(
                id=r.id, kind=r.kind, spec=r.spec, result=r.result, created_at=r.created_at
            )
            for r in session.results
        ],
    )
