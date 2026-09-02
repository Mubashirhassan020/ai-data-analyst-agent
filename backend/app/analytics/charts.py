"""Chart-spec generation: turns a chart request into Plotly-ready {data, layout}
JSON, grounded entirely in computed values from the dataframe (via the query and
correlation engines) — no fabricated data points, no placeholder series.

Pure functions over a Pandas DataFrame — no DB/storage/LLM access.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.common import json_safe
from app.analytics.correlation import compute_correlation
from app.analytics.query import _apply_filters, run_query
from app.core.errors import ValidationError

CHART_TYPES = {"bar", "grouped_bar", "line", "area", "scatter", "histogram", "box", "heatmap", "pie"}

# Category/slice caps: beyond these, the long tail is folded into "Other" rather
# than rendering an unreadable chart (spec: "pie/donut charts only when appropriate").
MAX_BAR_CATEGORIES = 20
MAX_PIE_SLICES = 8
MAX_BOX_GROUPS = 15

DEFAULT_HISTOGRAM_BINS = 30
DEFAULT_SCATTER_LIMIT = 2000
MAX_SCATTER_LIMIT = 10000


def _require_column(df: pd.DataFrame, name: str | None, label: str) -> str:
    if not name:
        raise ValidationError(f"'{label}' is required for this chart type.")
    if name not in df.columns:
        raise ValidationError(f"Unknown column: {name!r}")
    return name


def _require_numeric(df: pd.DataFrame, name: str, label: str) -> None:
    if not pd.api.types.is_numeric_dtype(df[name]):
        raise ValidationError(f"'{label}' column {name!r} must be numeric.")


def _granularity_for_span(span_days: float | None) -> str:
    if span_days is None or span_days <= 60:
        return "D"
    if span_days <= 730:
        return "W"
    return "M"


def _bucket_datetime(s: pd.Series, granularity: str) -> pd.Series:
    return s.dt.to_period(granularity).dt.start_time


def _top_n_with_other(df: pd.DataFrame, cat_col: str, value_col: str, n: int) -> pd.DataFrame:
    """Keep the top n-1 categories by value plus one "Other" bucket, so the
    output never exceeds n slices/bars total (not n+1)."""
    ranked = df.sort_values(value_col, ascending=False)
    if len(ranked) <= n:
        return ranked
    head, tail = ranked.iloc[: n - 1], ranked.iloc[n - 1 :]
    other = pd.DataFrame([{cat_col: "Other", value_col: tail[value_col].sum()}])
    return pd.concat([head, other], ignore_index=True)


def _aggregate(df: pd.DataFrame, x: str, y: str | None, aggregation: str | None, group_by: str | None) -> pd.DataFrame:
    metric = {"aggregation": aggregation or ("sum" if y else "count"), "column": y, "alias": "value"}
    group_cols = [x] + ([group_by] if group_by else [])
    result = run_query(df, group_by=group_cols, metrics=[metric])
    return pd.DataFrame(result["rows"])


def _series(vals: pd.Series) -> list[Any]:
    return [json_safe(v) for v in vals.tolist()]


def _histogram(work: pd.DataFrame, x: str | None, bins: int | None, title: str | None) -> dict[str, Any]:
    col = _require_column(work, x, "x")
    _require_numeric(work, col, "x")
    values = work[col].dropna()
    if values.empty:
        raise ValidationError(f"No data to plot for {col!r}.")
    trace = {"type": "histogram", "x": _series(values), "nbinsx": bins or DEFAULT_HISTOGRAM_BINS, "name": col}
    layout = {"title": title or f"Distribution of {col}", "xaxis": {"title": col}, "yaxis": {"title": "Count"}}
    return {"data": [trace], "layout": layout, "row_count": int(len(values))}


def _box(work: pd.DataFrame, x: str | None, y: str | None, title: str | None) -> dict[str, Any]:
    y_col = _require_column(work, y, "y")
    _require_numeric(work, y_col, "y")
    if x:
        if x not in work.columns:
            raise ValidationError(f"Unknown column: {x!r}")
        sub = work[[x, y_col]].dropna()
        groups = list(sub.groupby(x))
        if len(groups) > MAX_BOX_GROUPS:
            raise ValidationError(
                f"'{x}' has {len(groups)} distinct groups — too many for a readable box plot "
                f"(max {MAX_BOX_GROUPS}). Filter the data or pick a lower-cardinality column."
            )
        traces = [{"type": "box", "y": _series(g[y_col]), "name": str(cat)} for cat, g in groups]
        layout = {"title": title or f"{y_col} by {x}", "yaxis": {"title": y_col}}
    else:
        values = work[y_col].dropna()
        traces = [{"type": "box", "y": _series(values), "name": y_col}]
        layout = {"title": title or f"Distribution of {y_col}", "yaxis": {"title": y_col}}
    return {"data": traces, "layout": layout, "row_count": int(len(work))}


def _bar_or_pie(
    work: pd.DataFrame, chart_type: str, x: str | None, y: str | None,
    aggregation: str | None, group_by: str | None, title: str | None,
) -> dict[str, Any]:
    x_col = _require_column(work, x, "x")
    if y:
        _require_numeric(work, y, "y")
    if chart_type == "grouped_bar" and not group_by:
        raise ValidationError("'grouped_bar' requires a `group_by` column.")
    if chart_type == "pie" and group_by:
        raise ValidationError("'pie' does not support `group_by`.")

    agg_df = _aggregate(work, x_col, y, aggregation, group_by if chart_type != "pie" else None)
    if agg_df.empty:
        raise ValidationError("No data to plot after filtering.")
    y_label = y or "Count"

    if chart_type == "pie":
        capped = _top_n_with_other(agg_df, x_col, "value", MAX_PIE_SLICES)
        trace = {"type": "pie", "labels": _series(capped[x_col]), "values": _series(capped["value"])}
        layout = {"title": title or f"{y_label} share by {x_col}"}
        return {"data": [trace], "layout": layout, "row_count": int(len(work))}

    if group_by:
        traces = []
        for cat, g in agg_df.groupby(group_by):
            g_sorted = g.sort_values(x_col)
            traces.append({
                "type": "bar", "x": _series(g_sorted[x_col]), "y": _series(g_sorted["value"]), "name": str(cat),
            })
        layout = {
            "title": title or f"{y_label} by {x_col} and {group_by}",
            "barmode": "group", "xaxis": {"title": x_col}, "yaxis": {"title": y_label},
        }
    else:
        capped = (
            _top_n_with_other(agg_df, x_col, "value", MAX_BAR_CATEGORIES)
            if len(agg_df) > MAX_BAR_CATEGORIES
            else agg_df.sort_values("value", ascending=False)
        )
        traces = [{"type": "bar", "x": _series(capped[x_col]), "y": _series(capped["value"]), "name": y_label}]
        layout = {"title": title or f"{y_label} by {x_col}", "xaxis": {"title": x_col}, "yaxis": {"title": y_label}}

    return {"data": traces, "layout": layout, "row_count": int(len(work))}


def _line_or_area(
    work: pd.DataFrame, chart_type: str, x: str | None, y: str | None,
    aggregation: str | None, group_by: str | None, title: str | None,
) -> dict[str, Any]:
    x_col = _require_column(work, x, "x")
    if y:
        _require_numeric(work, y, "y")

    work = work.copy()
    if not pd.api.types.is_datetime64_any_dtype(work[x_col]):
        parsed = pd.to_datetime(work[x_col], errors="coerce", format="mixed")
        if parsed.notna().sum() == 0:
            raise ValidationError(f"'{x_col}' does not contain parseable dates.")
        work[x_col] = parsed

    valid_dates = work[x_col].dropna()
    span_days = (valid_dates.max() - valid_dates.min()).days if not valid_dates.empty else None
    granularity = _granularity_for_span(span_days)
    work["__bucket__"] = _bucket_datetime(work[x_col], granularity)

    agg_df = _aggregate(work, "__bucket__", y, aggregation, group_by).sort_values("__bucket__")
    y_label = y or "Count"
    fill = "tozeroy" if chart_type == "area" else None

    if group_by:
        traces = []
        for cat, g in agg_df.groupby(group_by):
            g_sorted = g.sort_values("__bucket__")
            trace = {
                "type": "scatter", "mode": "lines+markers",
                "x": _series(g_sorted["__bucket__"]), "y": _series(g_sorted["value"]), "name": str(cat),
            }
            if fill:
                trace["fill"] = fill
            traces.append(trace)
    else:
        trace = {
            "type": "scatter", "mode": "lines+markers",
            "x": _series(agg_df["__bucket__"]), "y": _series(agg_df["value"]), "name": y_label,
        }
        if fill:
            trace["fill"] = fill
        traces = [trace]

    layout = {
        "title": title or f"{y_label} over time ({granularity})",
        "xaxis": {"title": x_col}, "yaxis": {"title": y_label},
    }
    return {"data": traces, "layout": layout, "row_count": int(len(work)), "granularity": granularity}


def _scatter(
    work: pd.DataFrame, x: str | None, y: str | None, group_by: str | None, limit: int | None,
    title: str | None,
) -> dict[str, Any]:
    x_col = _require_column(work, x, "x")
    y_col = _require_column(work, y, "y")
    _require_numeric(work, x_col, "x")
    _require_numeric(work, y_col, "y")

    keep = [x_col, y_col] + ([group_by] if group_by else [])
    sub = work[keep].dropna(subset=[x_col, y_col])
    total = int(len(sub))
    eff_limit = min(limit or DEFAULT_SCATTER_LIMIT, MAX_SCATTER_LIMIT)
    sub = sub.head(eff_limit)

    if group_by:
        traces = [
            {"type": "scatter", "mode": "markers", "x": _series(g[x_col]), "y": _series(g[y_col]), "name": str(cat)}
            for cat, g in sub.groupby(group_by)
        ]
    else:
        traces = [{"type": "scatter", "mode": "markers", "x": _series(sub[x_col]), "y": _series(sub[y_col]), "name": f"{y_col} vs {x_col}"}]

    layout = {"title": title or f"{y_col} vs {x_col}", "xaxis": {"title": x_col}, "yaxis": {"title": y_col}}
    return {"data": traces, "layout": layout, "row_count": int(len(sub)), "truncated": total > eff_limit}


def _heatmap(work: pd.DataFrame, columns: list[str] | None, title: str | None) -> dict[str, Any]:
    corr = compute_correlation(work, columns=columns, method="pearson")
    trace = {
        "type": "heatmap", "z": corr["matrix"], "x": corr["columns"], "y": corr["columns"],
        "colorscale": "RdBu", "zmin": -1, "zmax": 1,
    }
    layout = {"title": title or "Correlation heatmap"}
    return {"data": [trace], "layout": layout, "row_count": int(len(work))}


def build_chart(
    df: pd.DataFrame,
    *,
    chart_type: str,
    x: str | None = None,
    y: str | None = None,
    aggregation: str | None = None,
    group_by: str | None = None,
    columns: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    limit: int | None = None,
    bins: int | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    if chart_type not in CHART_TYPES:
        raise ValidationError(f"Unsupported chart type: {chart_type!r}")

    work = _apply_filters(df, filters) if filters else df
    if work.empty:
        raise ValidationError("No rows match the given filters.")

    if chart_type == "histogram":
        spec = _histogram(work, x, bins, title)
    elif chart_type == "box":
        spec = _box(work, x, y, title)
    elif chart_type in ("bar", "grouped_bar", "pie"):
        spec = _bar_or_pie(work, chart_type, x, y, aggregation, group_by, title)
    elif chart_type in ("line", "area"):
        spec = _line_or_area(work, chart_type, x, y, aggregation, group_by, title)
    elif chart_type == "scatter":
        spec = _scatter(work, x, y, group_by, limit, title)
    else:  # heatmap
        spec = _heatmap(work, columns, title)

    spec.setdefault("truncated", False)
    spec.setdefault("granularity", None)
    return {"chart_type": chart_type, **spec}
