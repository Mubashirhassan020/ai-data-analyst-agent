"""Orchestrates ML: suggest viable tasks, dispatch training to the right engine,
and persist the resulting model + evaluation as an `ml_models` row. Training is
synchronous (consistent with every other analytics endpoint in this app) and
only ever persists on success — a failed request never reaches the database,
so there's no "failed" row to clean up or reconcile."""
from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db import models
from app.ml.anomaly import detect_anomalies
from app.ml.classification import train_classifier
from app.ml.clustering import train_clustering
from app.ml.regression import train_regressor
from app.ml.suggest import suggest_ml_tasks
from app.schemas.ml import MLTrainRequest
from app.services.dataset_service import DatasetService
from app.services.profiling_service import ProfilingService
from app.storage.base import Storage

log = get_logger(__name__)


def _model_to_dict(m: models.MLModel) -> dict[str, Any]:
    result = dict(m.result or {})
    return {
        "model_id": m.id,
        "dataset_id": m.dataset_id,
        "task": m.task,
        "algorithm": m.algorithm,
        "target": m.target,
        "features": m.features,
        "metrics": m.metrics,
        "feature_importance": result.get("feature_importance", []),
        "confusion_matrix": result.get("confusion_matrix"),
        "cluster_sizes": result.get("cluster_sizes"),
        "centroids": result.get("centroids"),
        "sample_rows": result.get("sample_rows"),
        "train_rows": result.get("train_rows"),
        "test_rows": result.get("test_rows"),
        "rows_used": result.get("rows_used"),
        "created_at": m.created_at,
    }


class MLService:
    def __init__(self, db: Session, storage: Storage) -> None:
        self.db = db
        self.dataset_service = DatasetService(db, storage)
        self.profiling_service = ProfilingService(db, storage)

    def suggest(self, dataset_id: str) -> dict[str, Any]:
        profile = self.profiling_service.get_or_compute(dataset_id)
        return {"dataset_id": dataset_id, "suggestions": suggest_ml_tasks(profile)}

    def train(self, req: MLTrainRequest) -> dict[str, Any]:
        self.dataset_service.get(req.dataset_id)
        df = self.dataset_service.load_dataframe(req.dataset_id)
        result = self._run(req, df)

        model_row = models.MLModel(
            dataset_id=req.dataset_id,
            task=req.task,
            target=req.target,
            features=req.features,
            algorithm=result["algorithm"],
            params=req.model_dump(exclude={"dataset_id"}),
            metrics=result.get("metrics", {}),
            result=result,
            status="completed",
        )
        self.db.add(model_row)
        self.db.commit()
        self.db.refresh(model_row)

        log.info(
            "ml_model_trained",
            dataset_id=req.dataset_id,
            model_id=model_row.id,
            task=req.task,
            algorithm=result["algorithm"],
        )
        return _model_to_dict(model_row)

    def get_model(self, model_id: str) -> dict[str, Any]:
        model = self.db.get(models.MLModel, model_id)
        if model is None:
            raise NotFoundError(f"ML model {model_id} not found.")
        return _model_to_dict(model)

    def _run(self, req: MLTrainRequest, df: pd.DataFrame) -> dict[str, Any]:
        if req.task == "classification":
            return train_classifier(
                df, target=req.target, features=req.features,
                algorithm=req.algorithm or "logistic_regression",
                test_size=req.test_size, random_state=req.random_state,
            )
        if req.task == "regression":
            return train_regressor(
                df, target=req.target, features=req.features,
                algorithm=req.algorithm or "linear_regression",
                test_size=req.test_size, random_state=req.random_state,
            )
        if req.task == "clustering":
            return train_clustering(
                df, features=req.features, n_clusters=req.n_clusters, random_state=req.random_state,
            )
        if req.task == "anomaly_detection":
            return detect_anomalies(
                df, features=req.features, contamination=req.contamination, random_state=req.random_state,
            )
        raise ValidationError(f"Unsupported task: {req.task!r}")
