"""Regression: Linear Regression, Random Forest, and Gradient Boosting, with
train/test split and MAE/MSE/RMSE/R² metrics."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.core.errors import ValidationError
from app.ml.common import (
    MIN_ROWS,
    build_preprocessor,
    extract_feature_importance,
    split_feature_types,
)


def _make_model(algorithm: str, random_state: int):
    if algorithm == "linear_regression":
        return LinearRegression()
    if algorithm == "random_forest":
        return RandomForestRegressor(n_estimators=200, random_state=random_state)
    if algorithm == "gradient_boosting":
        return GradientBoostingRegressor(random_state=random_state)
    raise ValidationError(
        f"Unsupported regression algorithm: {algorithm!r}. "
        "Choose from ['linear_regression', 'random_forest', 'gradient_boosting']."
    )


def train_regressor(
    df: pd.DataFrame,
    *,
    target: str,
    features: list[str],
    algorithm: str = "linear_regression",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    if target not in df.columns:
        raise ValidationError(f"Unknown target column: {target!r}")
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise ValidationError(f"Unknown feature column(s): {missing}")
    if target in features:
        raise ValidationError("Target column must not also be a feature column.")
    if not pd.api.types.is_numeric_dtype(df[target]):
        raise ValidationError(f"Target {target!r} must be numeric for regression.")

    work = df[features + [target]].dropna(subset=[target])
    if len(work) < MIN_ROWS:
        raise ValidationError(f"Not enough rows to train: {len(work)} found, at least {MIN_ROWS} required.")
    if work[target].nunique() < 2:
        raise ValidationError(f"Target {target!r} has a single constant value — nothing to regress.")

    X, y = work[features], work[target]
    numeric_cols, categorical_cols = split_feature_types(X, features)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    model = _make_model(algorithm, random_state)
    pipeline = Pipeline([("prep", build_preprocessor(numeric_cols, categorical_cols)), ("model", model)])
    try:
        pipeline.fit(X_train, y_train)
    except Exception as e:
        raise ValidationError(f"Could not train {algorithm}: {e}") from e

    y_pred = pipeline.predict(X_test)
    mse = float(mean_squared_error(y_test, y_pred))

    metrics = {
        "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
        "mse": round(mse, 4),
        "rmse": round(float(np.sqrt(mse)), 4),
        "r2": round(float(r2_score(y_test, y_pred)), 4),
    }

    return {
        "task": "regression",
        "algorithm": algorithm,
        "target": target,
        "features": features,
        "metrics": metrics,
        "feature_importance": extract_feature_importance(pipeline, numeric_cols, categorical_cols),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
    }
