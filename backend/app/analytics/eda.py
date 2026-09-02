"""Automated EDA: picks sensible chart suggestions from a computed profile,
grounded in actual column types and cardinality rather than a fixed template —
so a dataset with no dates gets no time-series chart, one with no numeric
measures gets no heatmap, etc. ("Do not generate meaningless charts.")
"""
from __future__ import annotations

from typing import Any

from app.analytics.correlation import STRONG_CORRELATION_THRESHOLD, compute_correlation
from app.core.errors import ValidationError

MAX_SUGGESTIONS = 8
MAX_CATEGORICAL_CARDINALITY_FOR_BAR = 20
MODERATE_CORRELATION_THRESHOLD = 0.5


def suggest_charts(df: Any, profile: dict[str, Any]) -> list[dict[str, Any]]:
    columns = profile["columns"]
    numeric_measures = [
        c["name"] for c in columns if c["inferred_type"] in ("integer", "float") and c["logical_type"] == "measure"
    ]
    categoricals = [
        c["name"] for c in columns
        if c["inferred_type"] == "categorical" and c["unique_count"] <= MAX_CATEGORICAL_CARDINALITY_FOR_BAR
    ]
    datetimes = [c["name"] for c in columns if c["inferred_type"] == "datetime"]

    suggestions: list[dict[str, Any]] = []

    for col in numeric_measures[:3]:
        suggestions.append({
            "chart_type": "histogram", "x": col, "title": f"Distribution of {col}",
            "reason": f"'{col}' is a numeric measure — a histogram shows its distribution.",
        })

    primary_measure = numeric_measures[0] if numeric_measures else None
    for col in categoricals[:3]:
        cardinality = next(c["unique_count"] for c in columns if c["name"] == col)
        suggestions.append({
            "chart_type": "bar", "x": col, "y": primary_measure,
            "aggregation": "sum" if primary_measure else "count",
            "title": f"{'Total ' + primary_measure if primary_measure else 'Count'} by {col}",
            "reason": f"'{col}' is categorical with {cardinality} distinct values.",
        })

    if datetimes and numeric_measures:
        dcol = datetimes[0]
        for mcol in numeric_measures[:2]:
            suggestions.append({
                "chart_type": "line", "x": dcol, "y": mcol, "aggregation": "sum",
                "title": f"{mcol} over time",
                "reason": f"'{dcol}' is a date column paired with numeric measure '{mcol}'.",
            })

    if len(numeric_measures) >= 2:
        suggestions.append({
            "chart_type": "heatmap", "columns": numeric_measures[:8], "title": "Correlation heatmap",
            "reason": f"{len(numeric_measures)} numeric measures are present — a heatmap shows how they relate.",
        })
        try:
            corr = compute_correlation(df, columns=numeric_measures, method="pearson")
        except ValidationError:
            corr = None
        if corr and corr["strong_pairs"]:
            top = corr["strong_pairs"][0]
            strength = "strongly" if abs(top["correlation"]) >= STRONG_CORRELATION_THRESHOLD else "moderately"
            suggestions.append({
                "chart_type": "scatter", "x": top["column_a"], "y": top["column_b"],
                "title": f"{top['column_b']} vs {top['column_a']}",
                "reason": (
                    f"'{top['column_a']}' and '{top['column_b']}' are {strength} correlated "
                    f"(r={top['correlation']})."
                ),
            })

    return suggestions[:MAX_SUGGESTIONS]
