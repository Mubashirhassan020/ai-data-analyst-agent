from __future__ import annotations

from pydantic import BaseModel


class NumericStats(BaseModel):
    count: int
    mean: float | None
    median: float | None
    std: float | None
    min: float | None
    max: float | None
    q1: float | None
    q3: float | None
    skewness: float | None
    outlier_count: int
    outlier_percentage: float


class CategoryCount(BaseModel):
    value: str
    count: int
    percentage: float


class CategoricalStats(BaseModel):
    distinct_count: int
    top_categories: list[CategoryCount]


class DatetimeStats(BaseModel):
    min_date: str | None
    max_date: str | None
    range_days: int | None
    invalid_count: int
    invalid_percentage: float


class BooleanStats(BaseModel):
    true_count: int
    false_count: int


class ColumnProfile(BaseModel):
    name: str
    position: int
    inferred_type: str
    logical_type: str
    null_count: int
    null_percentage: float
    unique_count: int
    cardinality_ratio: float
    min_value: str | None
    max_value: str | None
    numeric: NumericStats | None
    categorical: CategoricalStats | None
    datetime: DatetimeStats | None
    boolean: BooleanStats | None


class Issue(BaseModel):
    type: str
    column: str | None
    severity: str
    message: str


class QualityScore(BaseModel):
    overall: int
    completeness: float
    missing_values: float
    duplicates: float
    data_types: float
    outliers: float


class DatasetProfileOut(BaseModel):
    dataset_id: str
    row_count: int
    column_count: int
    missing_cells: int
    missing_percentage: float
    duplicate_rows: int
    duplicate_percentage: float
    columns: list[ColumnProfile]
    issues: list[Issue]
    quality: QualityScore
    generated_at: str
    cached: bool = False
