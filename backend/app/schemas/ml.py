from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

MLTask = Literal["classification", "regression", "clustering", "anomaly_detection"]


class MLSuggestRequest(BaseModel):
    dataset_id: str


class MLSuggestion(BaseModel):
    task: MLTask
    target: str | None = None
    features: list[str]
    reason: str


class MLSuggestionsResponse(BaseModel):
    dataset_id: str
    suggestions: list[MLSuggestion]


class MLTrainRequest(BaseModel):
    dataset_id: str
    task: MLTask
    target: str | None = None
    features: list[str] = Field(min_length=1)
    algorithm: str | None = None
    test_size: float = Field(0.2, gt=0, lt=0.9)
    n_clusters: int = Field(3, ge=2, le=50)
    contamination: float = Field(0.05, gt=0, le=0.5)
    random_state: int = 42
    title: str | None = None

    @model_validator(mode="after")
    def _validate_task_shape(self) -> MLTrainRequest:
        if self.task in ("classification", "regression") and not self.target:
            raise ValueError(f"task {self.task!r} requires a target column.")
        if self.target and self.target in self.features:
            raise ValueError("target column must not also be a feature column.")
        return self


class FeatureImportance(BaseModel):
    feature: str
    importance: float
    importance_pct: float


class ConfusionMatrix(BaseModel):
    labels: list[str]
    matrix: list[list[int]]


class MLModelOut(BaseModel):
    model_id: str
    dataset_id: str
    task: str
    algorithm: str
    target: str | None
    features: list[str]
    metrics: dict[str, Any]
    feature_importance: list[FeatureImportance] = Field(default_factory=list)
    confusion_matrix: ConfusionMatrix | None = None
    cluster_sizes: dict[str, int] | None = None
    centroids: list[list[float | None]] | None = None
    sample_rows: list[dict[str, Any]] | None = None
    train_rows: int | None = None
    test_rows: int | None = None
    rows_used: int | None = None
    created_at: datetime
