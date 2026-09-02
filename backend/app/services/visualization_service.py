"""Orchestrates chart building: load data, build a Plotly spec, persist it under
an analysis session (same pattern as AnalyticsService.execute), and auto-suggest
EDA charts from a dataset's computed profile."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analytics.charts import build_chart
from app.analytics.eda import suggest_charts
from app.core.errors import ValidationError
from app.core.logging import get_logger
from app.db import models
from app.schemas.chart import ChartRequest
from app.services.dataset_service import DatasetService
from app.services.profiling_service import ProfilingService
from app.services.session_helper import get_or_create_analysis_session
from app.storage.base import Storage

log = get_logger(__name__)


class VisualizationService:
    def __init__(self, db: Session, storage: Storage) -> None:
        self.db = db
        self.dataset_service = DatasetService(db, storage)
        self.profiling_service = ProfilingService(db, storage)

    def build(self, req: ChartRequest) -> dict:
        self.dataset_service.get(req.dataset_id)
        df = self.dataset_service.load_dataframe(req.dataset_id)

        spec = build_chart(
            df,
            chart_type=req.chart_type,
            x=req.x,
            y=req.y,
            aggregation=req.aggregation,
            group_by=req.group_by,
            columns=req.columns,
            filters=[f.model_dump() for f in req.filters],
            limit=req.limit,
            bins=req.bins,
            title=req.title,
        )

        session = get_or_create_analysis_session(self.db, req.dataset_id, req.session_id, req.title)
        spec_dict = req.model_dump(exclude={"session_id"})
        record = models.AnalysisResult(session_id=session.id, kind="chart", spec=spec_dict, result=spec)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        log.info(
            "chart_built",
            dataset_id=req.dataset_id,
            chart_type=req.chart_type,
            session_id=session.id,
            result_id=record.id,
        )
        return {**spec, "session_id": session.id, "result_id": record.id, "spec": spec_dict}

    def suggest(self, dataset_id: str) -> dict:
        profile = self.profiling_service.get_or_compute(dataset_id)
        df = self.dataset_service.load_dataframe(dataset_id)

        built = []
        for suggestion in suggest_charts(df, profile):
            try:
                spec = build_chart(
                    df,
                    chart_type=suggestion["chart_type"],
                    x=suggestion.get("x"),
                    y=suggestion.get("y"),
                    aggregation=suggestion.get("aggregation"),
                    group_by=suggestion.get("group_by"),
                    columns=suggestion.get("columns"),
                    title=suggestion.get("title"),
                )
                built.append({**spec, "reason": suggestion["reason"]})
            except ValidationError as e:
                log.warning("eda_suggestion_skipped", dataset_id=dataset_id, reason=str(e))
                continue

        return {"dataset_id": dataset_id, "charts": built}
