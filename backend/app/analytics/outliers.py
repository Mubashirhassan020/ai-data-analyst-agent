"""Univariate outlier detection: IQR and Z-score. Pure function.

Isolation Forest (multivariate) is added alongside the ML service once
scikit-learn model training is wired up — these two methods cover the
common single-column "is this value unusual" case without that dependency.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics.common import to_records
from app.core.errors import ValidationError

SAMPLE_ROWS_PER_COLUMN = 20
ZSCORE_THRESHOLD = 3.0


def _iqr_deviation(non_null: pd.Series) -> tuple[pd.Series, pd.Series]:
    q1, q3 = non_null.quantile(0.25), non_null.quantile(0.75)
    iqr = q3 - q1
    if iqr <= 0:
        zeros = pd.Series(0.0, index=non_null.index)
        return zeros, zeros > 0
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    deviation = (non_null - upper).clip(lower=0) + (lower - non_null).clip(lower=0)
    return deviation, deviation > 0


def _zscore_deviation(non_null: pd.Series) -> tuple[pd.Series, pd.Series]:
    std = non_null.std()
    if not std or std <= 0:
        zeros = pd.Series(0.0, index=non_null.index)
        return zeros, zeros > 0
    z = (non_null - non_null.mean()) / std
    deviation = z.abs()
    return deviation, deviation > ZSCORE_THRESHOLD


def detect_outliers(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    method: str = "iqr",
) -> dict[str, Any]:
    numeric_df = df.select_dtypes(include=[np.number])
    cols = columns or list(numeric_df.columns)
    missing = [c for c in cols if c not in numeric_df.columns]
    if missing:
        raise ValidationError(
            f"Columns are not numeric or not found: {missing}",
            details={"numeric_columns": list(numeric_df.columns)},
        )
    if method not in ("iqr", "zscore"):
        raise ValidationError(f"Unsupported outlier method: {method!r}")

    results = []
    for col in cols:
        non_null = df[col].dropna()
        if non_null.empty:
            results.append({
                "column": col, "method": method, "outlier_count": 0,
                "outlier_percentage": 0.0, "sample_rows": [],
            })
            continue

        deviation, mask = _iqr_deviation(non_null) if method == "iqr" else _zscore_deviation(non_null)
        outlier_count = int(mask.sum())
        top_idx = deviation[mask].sort_values(ascending=False).index[:SAMPLE_ROWS_PER_COLUMN]
        sample_rows = to_records(df.loc[top_idx])

        results.append({
            "column": col,
            "method": method,
            "outlier_count": outlier_count,
            "outlier_percentage": round(100 * outlier_count / len(non_null), 4),
            "sample_rows": sample_rows,
        })

    return {"method": method, "columns": results}
