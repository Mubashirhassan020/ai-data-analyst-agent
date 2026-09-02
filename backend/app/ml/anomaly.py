"""Multivariate anomaly detection via Isolation Forest — the counterpart to
the univariate IQR/Z-score methods in app/analytics/outliers.py (Phase 5),
which explicitly deferred this multivariate case to here."""
from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.ensemble import IsolationForest

from app.analytics.common import to_records
from app.core.errors import ValidationError
from app.ml.common import MIN_ROWS

SAMPLE_ROWS = 20


def detect_anomalies(
    df: pd.DataFrame,
    *,
    features: list[str],
    contamination: float = 0.05,
    random_state: int = 42,
) -> dict[str, Any]:
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise ValidationError(f"Unknown feature column(s): {missing}")
    non_numeric = [f for f in features if not pd.api.types.is_numeric_dtype(df[f])]
    if non_numeric:
        raise ValidationError(f"Anomaly detection requires numeric columns; not numeric: {non_numeric}")

    work = df[features].dropna()
    if len(work) < MIN_ROWS:
        raise ValidationError(f"Not enough rows to run: {len(work)} found, at least {MIN_ROWS} required.")

    model = IsolationForest(contamination=contamination, random_state=random_state)
    try:
        predictions = model.fit_predict(work)
        scores = model.decision_function(work)
    except Exception as e:
        raise ValidationError(f"Could not fit Isolation Forest: {e}") from e

    is_anomaly = predictions == -1
    anomaly_count = int(is_anomaly.sum())

    scored = pd.Series(scores, index=work.index)
    top_anomaly_idx = scored[is_anomaly].sort_values().index[:SAMPLE_ROWS]

    return {
        "task": "anomaly_detection",
        "algorithm": "isolation_forest",
        "features": features,
        "metrics": {
            "anomaly_count": anomaly_count,
            "anomaly_percentage": round(100 * anomaly_count / len(work), 4),
        },
        "sample_rows": to_records(df.loc[top_anomaly_idx]),
        "rows_used": int(len(work)),
    }
