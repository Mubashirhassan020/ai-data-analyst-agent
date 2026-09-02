"""Orchestrates the analytics engine: load data, run a query/correlation/outlier
computation, and (for /execute) persist the result under an analysis session."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analytics.correlation import compute_correlation
from app.analytics.forecasting import forecast as run_forecast
from app.analytics.outliers import detect_outliers
from app.analytics.query import run_query
from app.analytics.sql_engine import run_sql
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.db import models
from app.schemas.analysis import (
    AnalysisRequest,
    CorrelationRequest,
    ForecastRequest,
    OutlierRequest,
    SqlRequest,
)
from app.services.dataset_service import DatasetService
from app.services.session_helper import get_or_create_analysis_session
from app.storage.base import Storage

log = get_logger(__name__)


class AnalyticsService:
    def __init__(self, db: Session, storage: Storage) -> None:
        self.db = db
        self.dataset_service = DatasetService(db, storage)

    def execute(self, spec: AnalysisRequest) -> dict:
        self.dataset_service.get(spec.dataset_id)
        df = self.dataset_service.load_dataframe(spec.dataset_id)

        result = run_query(
            df,
            filters=[f.model_dump() for f in spec.filters],
            group_by=spec.group_by,
            metrics=[m.model_dump() for m in spec.metrics],
            sort=spec.sort.model_dump() if spec.sort else None,
            limit=spec.limit,
        )

        session = get_or_create_analysis_session(self.db, spec.dataset_id, spec.session_id, spec.title)
        spec_dict = spec.model_dump(exclude={"session_id"})
        record = models.AnalysisResult(session_id=session.id, kind="table", spec=spec_dict, result=result)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        log.info(
            "analysis_executed",
            dataset_id=spec.dataset_id,
            session_id=session.id,
            result_id=record.id,
            rows=result["row_count"],
        )
        return {**result, "session_id": session.id, "result_id": record.id, "spec": spec_dict}

    def correlation(self, req: CorrelationRequest) -> dict:
        df = self.dataset_service.load_dataframe(req.dataset_id)
        return compute_correlation(df, columns=req.columns, method=req.method)

    def outliers(self, req: OutlierRequest) -> dict:
        df = self.dataset_service.load_dataframe(req.dataset_id)
        return detect_outliers(df, columns=req.columns, method=req.method)

    def sql(self, req: SqlRequest) -> dict:
        self.dataset_service.get(req.dataset_id)
        df = self.dataset_service.load_dataframe(req.dataset_id)
        result = run_sql(df, req.sql)

        session = get_or_create_analysis_session(self.db, req.dataset_id, req.session_id, req.title)
        spec_dict = req.model_dump(exclude={"session_id"})
        record = models.AnalysisResult(session_id=session.id, kind="sql", spec=spec_dict, result=result)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        log.info("sql_executed", dataset_id=req.dataset_id, session_id=session.id, result_id=record.id)
        return {**result, "session_id": session.id, "result_id": record.id, "spec": spec_dict}

    def forecast(self, req: ForecastRequest) -> dict:
        self.dataset_service.get(req.dataset_id)
        df = self.dataset_service.load_dataframe(req.dataset_id)
        result = run_forecast(
            df,
            date_column=req.date_column,
            value_column=req.value_column,
            periods_ahead=req.periods_ahead,
            method=req.method,
            aggregation=req.aggregation,
        )

        session = get_or_create_analysis_session(self.db, req.dataset_id, req.session_id, req.title)
        spec_dict = req.model_dump(exclude={"session_id"})
        record = models.AnalysisResult(session_id=session.id, kind="forecast", spec=spec_dict, result=result)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        log.info("forecast_executed", dataset_id=req.dataset_id, session_id=session.id, result_id=record.id)
        return {**result, "session_id": session.id, "result_id": record.id, "spec": spec_dict}

    def get_session(self, session_id: str) -> models.AnalysisSession:
        session = self.db.get(models.AnalysisSession, session_id)
        if session is None:
            raise NotFoundError(f"Analysis session {session_id} not found.")
        return session
