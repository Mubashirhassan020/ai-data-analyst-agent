"""Shared helpers for the analytics layer: JSON-safe coercion of numpy/pandas scalars."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def json_safe(value: Any) -> Any:
    """Coerce a numpy/pandas scalar (including NaN/NaT/Timestamp) into a plain
    JSON-serializable Python value. `None` in, `None` out."""
    if value is None:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a dataframe to a list of JSON-safe row dicts (NaN -> None)."""
    safe = df.astype(object).where(pd.notnull(df), None)
    return [{k: json_safe(v) for k, v in row.items()} for row in safe.to_dict(orient="records")]
