"""Deterministic query execution: filter, group-by/aggregate, sort, limit.

Pure functions over a Pandas DataFrame — no DB/storage/LLM access. This is the
computation layer the Analysis Builder and (later) the AI agent's Pandas tool
call into. Every value returned here is computed directly from the dataframe;
nothing is inferred or guessed.

Only AND-combined filters are supported (no OR groups) — a deliberate
simplification. A richer boolean expression tree can be added later if a real
use case needs it.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.common import to_records
from app.core.errors import ValidationError

AGGREGATIONS = {"sum", "mean", "median", "count", "min", "max", "std"}
FILTER_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "is_null", "not_null"}

# Raw (non-aggregated) passthrough queries are capped by default to keep payloads
# bounded; callers can request more explicitly via `limit`.
DEFAULT_RAW_LIMIT = 1000
MAX_LIMIT = 5000


def _coerce_value(series: pd.Series, value: Any) -> Any:
    if pd.api.types.is_datetime64_any_dtype(series) and isinstance(value, str):
        try:
            return pd.to_datetime(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Could not parse {value!r} as a date.") from e
    if pd.api.types.is_numeric_dtype(series) and not isinstance(value, bool):
        try:
            return float(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Could not parse {value!r} as a number.") from e
    return value


def _apply_filters(df: pd.DataFrame, filters: list[dict[str, Any]]) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for f in filters:
        col, op, value = f["column"], f["operator"], f.get("value")
        if col not in df.columns:
            raise ValidationError(f"Unknown filter column: {col!r}")
        if op not in FILTER_OPERATORS:
            raise ValidationError(f"Unsupported filter operator: {op!r}")
        s = df[col]
        if op == "is_null":
            m = s.isna()
        elif op == "not_null":
            m = s.notna()
        elif op == "in":
            if not isinstance(value, list):
                raise ValidationError("`in` requires a list value.")
            m = s.isin(value)
        elif op == "not_in":
            if not isinstance(value, list):
                raise ValidationError("`not_in` requires a list value.")
            m = ~s.isin(value)
        elif op == "contains":
            m = s.astype(str).str.contains(str(value), case=False, na=False, regex=False)
        else:
            cv = _coerce_value(s, value)
            if op == "eq":
                m = s == cv
            elif op == "ne":
                m = s != cv
            elif op == "gt":
                m = s > cv
            elif op == "gte":
                m = s >= cv
            elif op == "lt":
                m = s < cv
            else:  # lte
                m = s <= cv
        mask &= m.fillna(False)
    return df[mask]


def _apply_aggregation(df: pd.DataFrame, group_by: list[str], metrics: list[dict[str, Any]]) -> pd.DataFrame:
    for col in group_by:
        if col not in df.columns:
            raise ValidationError(f"Unknown group_by column: {col!r}")

    grouped = df.groupby(group_by, dropna=False) if group_by else None
    pieces: list[pd.Series] = []

    metrics = metrics or [{"aggregation": "count", "column": None, "alias": None}]
    for m in metrics:
        agg, col, alias = m["aggregation"], m.get("column"), m.get("alias")
        if agg not in AGGREGATIONS:
            raise ValidationError(f"Unsupported aggregation: {agg!r}")
        if col is not None and col not in df.columns:
            raise ValidationError(f"Unknown metric column: {col!r}")
        alias = alias or (f"{agg}_{col}" if col else "count")

        if group_by:
            if agg == "count":
                s = grouped[col].count() if col else grouped.size()
            else:
                if col is None:
                    raise ValidationError(f"Aggregation {agg!r} requires a column.")
                s = grouped[col].agg(agg)
        else:
            if agg == "count":
                value = int(df[col].count()) if col else int(len(df))
            else:
                if col is None:
                    raise ValidationError(f"Aggregation {agg!r} requires a column.")
                value = getattr(df[col], agg)()
            s = pd.Series([value])
        s.name = alias
        pieces.append(s)

    result = pd.concat(pieces, axis=1)
    if group_by:
        result = result.reset_index()
    return result


def run_query(
    df: pd.DataFrame,
    *,
    filters: list[dict[str, Any]] | None = None,
    group_by: list[str] | None = None,
    metrics: list[dict[str, Any]] | None = None,
    sort: dict[str, Any] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    filters = filters or []
    group_by = group_by or []
    metrics = metrics or []

    working = _apply_filters(df, filters)

    if group_by or metrics:
        result_df = _apply_aggregation(working, group_by, metrics)
    else:
        result_df = working

    if sort:
        by = sort["by"]
        if by not in result_df.columns:
            raise ValidationError(
                f"Unknown sort column: {by!r}",
                details={"available": list(result_df.columns)},
            )
        result_df = result_df.sort_values(by=by, ascending=(sort.get("direction", "desc") == "asc"))

    total_matched = int(result_df.shape[0])

    effective_limit = limit
    if effective_limit is None and not group_by and not metrics:
        effective_limit = DEFAULT_RAW_LIMIT
    if effective_limit is not None:
        effective_limit = min(effective_limit, MAX_LIMIT)
        result_df = result_df.head(effective_limit)

    return {
        "columns": [str(c) for c in result_df.columns],
        "rows": to_records(result_df),
        "row_count": int(result_df.shape[0]),
        "total_matched_rows": total_matched,
        "truncated": int(result_df.shape[0]) < total_matched,
    }
