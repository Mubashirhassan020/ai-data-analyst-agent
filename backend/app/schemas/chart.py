from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import Aggregation, AnalysisFilter

ChartType = Literal["bar", "grouped_bar", "line", "area", "scatter", "histogram", "box", "heatmap", "pie"]


class ChartRequest(BaseModel):
    dataset_id: str
    chart_type: ChartType
    x: str | None = None
    y: str | None = None
    aggregation: Aggregation | None = None
    group_by: str | None = None
    columns: list[str] | None = None  # heatmap only
    filters: list[AnalysisFilter] = Field(default_factory=list)
    limit: int | None = Field(None, ge=1, le=10000)
    bins: int | None = Field(None, ge=5, le=200)
    title: str | None = None
    session_id: str | None = None


class ChartResult(BaseModel):
    session_id: str
    result_id: str
    chart_type: str
    data: list[dict[str, Any]]
    layout: dict[str, Any]
    row_count: int
    truncated: bool = False
    granularity: str | None = None
    spec: dict[str, Any]


class EDAChart(BaseModel):
    chart_type: str
    data: list[dict[str, Any]]
    layout: dict[str, Any]
    row_count: int
    truncated: bool = False
    granularity: str | None = None
    reason: str


class EDASuggestionsResponse(BaseModel):
    dataset_id: str
    charts: list[EDAChart]
