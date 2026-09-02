from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

FilterOperator = Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "is_null", "not_null"]
Aggregation = Literal["sum", "mean", "median", "count", "min", "max", "std"]


class AnalysisFilter(BaseModel):
    column: str
    operator: FilterOperator
    value: Any | None = None


class AnalysisMetric(BaseModel):
    column: str | None = None
    aggregation: Aggregation
    alias: str | None = None

    @model_validator(mode="after")
    def _column_required_unless_count(self) -> AnalysisMetric:
        if self.aggregation != "count" and not self.column:
            raise ValueError(f"Aggregation {self.aggregation!r} requires a column.")
        return self


class AnalysisSort(BaseModel):
    by: str
    direction: Literal["asc", "desc"] = "desc"


class AnalysisRequest(BaseModel):
    dataset_id: str
    filters: list[AnalysisFilter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    metrics: list[AnalysisMetric] = Field(default_factory=list)
    sort: AnalysisSort | None = None
    limit: int | None = Field(None, ge=1, le=5000)
    session_id: str | None = None
    title: str | None = None


class AnalysisResultOut(BaseModel):
    session_id: str
    result_id: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    total_matched_rows: int
    truncated: bool
    spec: dict[str, Any]


class AnalysisResultSummary(BaseModel):
    id: str
    kind: str
    spec: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime


class AnalysisSessionOut(BaseModel):
    id: str
    dataset_id: str
    title: str | None
    created_at: datetime
    results: list[AnalysisResultSummary]


class CorrelationRequest(BaseModel):
    dataset_id: str
    columns: list[str] | None = None
    method: Literal["pearson", "spearman", "kendall"] = "pearson"


class CorrelationPair(BaseModel):
    column_a: str
    column_b: str
    correlation: float


class CorrelationResult(BaseModel):
    columns: list[str]
    matrix: list[list[float | None]]
    strong_pairs: list[CorrelationPair]
    method: str


class OutlierRequest(BaseModel):
    dataset_id: str
    columns: list[str] | None = None
    method: Literal["iqr", "zscore"] = "iqr"


class OutlierColumnResult(BaseModel):
    column: str
    method: str
    outlier_count: int
    outlier_percentage: float
    sample_rows: list[dict[str, Any]]


class OutlierResult(BaseModel):
    method: str
    columns: list[OutlierColumnResult]


class SqlRequest(BaseModel):
    dataset_id: str
    sql: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    title: str | None = None


class SqlResult(BaseModel):
    session_id: str
    result_id: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    total_matched_rows: int
    truncated: bool
    sql: str
    spec: dict[str, Any]


ForecastMethod = Literal["naive", "moving_average", "linear", "exponential_smoothing"]


class ForecastRequest(BaseModel):
    dataset_id: str
    date_column: str
    value_column: str
    periods_ahead: int = Field(6, ge=1, le=24)
    method: ForecastMethod = "linear"
    aggregation: Aggregation = "sum"
    session_id: str | None = None
    title: str | None = None


class ForecastPoint(BaseModel):
    date: str
    value: float | None


class ForecastResult(BaseModel):
    session_id: str
    result_id: str
    method: str
    granularity: str
    date_column: str
    value_column: str
    historical: list[ForecastPoint]
    forecast: list[ForecastPoint]
    backtest_mae: float | None
    historical_periods: int
    spec: dict[str, Any]
