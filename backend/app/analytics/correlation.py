"""Pearson/Spearman/Kendall correlation between numeric columns. Pure function."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.core.errors import ValidationError

STRONG_CORRELATION_THRESHOLD = 0.7


def compute_correlation(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    method: str = "pearson",
) -> dict[str, Any]:
    numeric_df = df.select_dtypes(include=[np.number])

    if columns:
        missing = [c for c in columns if c not in numeric_df.columns]
        if missing:
            raise ValidationError(
                f"Columns are not numeric or not found: {missing}",
                details={"numeric_columns": list(numeric_df.columns)},
            )
        numeric_df = numeric_df[columns]

    if numeric_df.shape[1] < 2:
        raise ValidationError(
            "At least 2 numeric columns are required to compute correlation.",
            details={"numeric_columns": list(numeric_df.columns)},
        )

    corr = numeric_df.corr(method=method)
    cols = [str(c) for c in corr.columns]

    matrix: list[list[float | None]] = []
    for row in corr.values:
        matrix.append([None if (v is None or np.isnan(v)) else round(float(v), 4) for v in row])

    strong_pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if pd.notna(r) and abs(r) >= STRONG_CORRELATION_THRESHOLD:
                strong_pairs.append(
                    {"column_a": cols[i], "column_b": cols[j], "correlation": round(float(r), 4)}
                )
    strong_pairs.sort(key=lambda p: -abs(p["correlation"]))

    return {"columns": cols, "matrix": matrix, "strong_pairs": strong_pairs, "method": method}
