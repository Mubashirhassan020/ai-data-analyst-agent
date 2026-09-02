"""Gathers every real, already-computed piece of data a report needs into one
dict: dataset metadata, profile, quality, key statistics, a handful of charts,
anomalies, deterministic recommendations, and (if a chat session already
exists) the latest AI-generated insight. No LLM call happens during report
generation — reports summarize prior analysis, they don't trigger new AI work.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.correlation import compute_correlation
from app.analytics.outliers import detect_outliers
from app.core.errors import ValidationError
from app.db import models
from app.reports.chart_renderer import render_bar, render_heatmap, render_histogram, render_line
from app.services.dataset_service import DatasetService
from app.services.profiling_service import ProfilingService
from app.storage.base import Storage

MAX_CHARTS = 4
MAX_ANOMALY_COLUMNS = 3
MAX_ANOMALY_SAMPLE_ROWS = 5
MAX_RECOMMENDATIONS = 8


def build_report_data(db: Session, storage: Storage, dataset_id: str) -> dict[str, Any]:
    dataset_service = DatasetService(db, storage)
    profiling_service = ProfilingService(db, storage)

    ds = dataset_service.get(dataset_id)
    df = dataset_service.load_dataframe(dataset_id)
    profile = profiling_service.get_or_compute(dataset_id)

    dataset_info = {
        "id": ds.id,
        "filename": ds.original_filename,
        "row_count": ds.row_count,
        "column_count": ds.column_count,
        "size_bytes": ds.file_size_bytes,
        "uploaded_at": ds.created_at.isoformat(),
    }

    return {
        "dataset": dataset_info,
        "executive_summary": _build_executive_summary(dataset_info, profile),
        "profile": profile,
        "numeric_stats": [c for c in profile["columns"] if c["numeric"]],
        "categorical_stats": [c for c in profile["columns"] if c["categorical"]],
        "charts": _build_charts(df, profile),
        "anomalies": _build_anomalies(df, profile),
        "recommendations": _build_recommendations(profile),
        "ai_insight": _latest_ai_insight(db, dataset_id),
        "methodology": _METHODOLOGY,
        "limitations": _LIMITATIONS,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _build_executive_summary(dataset_info: dict[str, Any], profile: dict[str, Any]) -> str:
    q = profile["quality"]
    issue_count = len(profile["issues"])
    return (
        f"This dataset ('{dataset_info['filename']}') contains {profile['row_count']:,} rows and "
        f"{profile['column_count']} columns ({dataset_info['size_bytes']:,} bytes). "
        f"The overall data quality score is {q['overall']}/100. "
        f"{profile['missing_percentage']}% of all cells are missing and "
        f"{profile['duplicate_rows']} duplicate row(s) were found, with {issue_count} "
        f"data-quality issue(s) detected in total."
    )


def _build_charts(df: pd.DataFrame, profile: dict[str, Any]) -> list[dict[str, str]]:
    charts: list[dict[str, str]] = []
    columns = profile["columns"]
    numeric_measures = [
        c["name"] for c in columns if c["inferred_type"] in ("integer", "float") and c["logical_type"] == "measure"
    ]
    categoricals = [c for c in columns if c["inferred_type"] == "categorical"]
    datetimes = [c["name"] for c in columns if c["inferred_type"] == "datetime"]

    if numeric_measures:
        col = numeric_measures[0]
        title = f"Distribution of {col}"
        charts.append({"title": title, "image_base64": render_histogram(df[col].dropna().tolist(), title)})

    if categoricals and len(charts) < MAX_CHARTS:
        c = categoricals[0]
        top = c["categorical"]["top_categories"][:8]
        title = f"Top categories in {c['name']}"
        charts.append({
            "title": title,
            "image_base64": render_bar([t["value"] for t in top], [t["count"] for t in top], title, ylabel="Count"),
        })

    if datetimes and numeric_measures and len(charts) < MAX_CHARTS:
        dcol, mcol = datetimes[0], numeric_measures[0]
        ts = df[[dcol, mcol]].copy()
        ts[dcol] = pd.to_datetime(ts[dcol], errors="coerce", format="mixed")
        ts = ts.dropna(subset=[dcol]).sort_values(dcol)
        if not ts.empty:
            span = (ts[dcol].max() - ts[dcol].min()).days
            granularity = "D" if span <= 60 else ("W" if span <= 730 else "M")
            bucketed = ts.groupby(ts[dcol].dt.to_period(granularity).dt.start_time)[mcol].sum()
            if len(bucketed) >= 2:
                title = f"{mcol} over time"
                charts.append({
                    "title": title,
                    "image_base64": render_line(
                        [d.strftime("%Y-%m-%d") for d in bucketed.index], bucketed.tolist(), title, ylabel=mcol
                    ),
                })

    if len(numeric_measures) >= 2 and len(charts) < MAX_CHARTS:
        try:
            corr = compute_correlation(df, columns=numeric_measures[:8])
            charts.append({
                "title": "Correlation heatmap",
                "image_base64": render_heatmap(corr["columns"], corr["matrix"], "Correlation heatmap"),
            })
        except ValidationError:
            pass

    return charts[:MAX_CHARTS]


def _build_anomalies(df: pd.DataFrame, profile: dict[str, Any]) -> dict[str, Any]:
    numeric_measures = [
        c["name"] for c in profile["columns"] if c["inferred_type"] in ("integer", "float") and c["logical_type"] == "measure"
    ]
    if not numeric_measures:
        return {"columns": []}
    try:
        result = detect_outliers(df, columns=numeric_measures[:MAX_ANOMALY_COLUMNS], method="iqr")
    except ValidationError:
        return {"columns": []}
    for col in result["columns"]:
        col["sample_rows"] = col["sample_rows"][:MAX_ANOMALY_SAMPLE_ROWS]
    return result


_ISSUE_RECOMMENDATIONS = {
    "missing_values": lambda i: f"Address missing values in '{i['column']}' ({i['message']}) before using it in analysis or modeling.",
    "duplicate_rows": lambda i: f"Investigate and likely remove duplicate rows: {i['message']}",
    "extreme_outliers": lambda i: f"Review outliers in '{i['column']}' — {i['message']} They may be data errors or genuinely unusual events worth investigating.",
    "constant_column": lambda i: f"'{i['column']}' has no variation and can likely be dropped from analysis.",
    "high_cardinality_categorical": lambda i: f"'{i['column']}' has many distinct values — consider grouping rare categories before charting or modeling.",
    "invalid_dates": lambda i: f"Clean up unparseable date values in '{i['column']}'.",
}


def _build_recommendations(profile: dict[str, Any]) -> list[str]:
    recs = []
    for issue in profile["issues"]:
        builder = _ISSUE_RECOMMENDATIONS.get(issue["type"])
        if builder:
            recs.append(builder(issue))
    if profile["quality"]["overall"] >= 90 and not recs:
        recs.append("This dataset is in good shape overall — no major data-quality issues were detected.")
    return recs[:MAX_RECOMMENDATIONS]


def _latest_ai_insight(db: Session, dataset_id: str) -> dict[str, Any] | None:
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.dataset_id == dataset_id)
        .order_by(models.ChatSession.created_at.desc())
        .first()
    )
    if session is None:
        return None
    last_assistant = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id, models.ChatMessage.role == "assistant")
        .order_by(models.ChatMessage.created_at.desc())
        .first()
    )
    if last_assistant is None:
        return None
    return {"content": last_assistant.content, "generated_at": last_assistant.created_at.isoformat()}


_METHODOLOGY = (
    "Data quality score: five sub-scores (completeness, missing values, duplicates, data types, "
    "outliers), each 0-10, averaged to a 0-100 overall score. Column types are inferred from dtype "
    "and value patterns (e.g. a fully-unique short-token column is flagged as a likely identifier). "
    "Outliers use the IQR method (values beyond 1.5x the interquartile range). Correlation uses the "
    "Pearson coefficient; pairs with |r| >= 0.7 are called 'strong'. All statistics are computed "
    "directly from the uploaded data — nothing in this report is estimated or inferred by a language model."
)

_LIMITATIONS = (
    "This report reflects a snapshot of the dataset at generation time. Outlier and correlation "
    "detection use single, well-known methods (IQR, Pearson) rather than an ensemble of techniques. "
    "Charts are limited to a representative subset of columns for readability. The 'AI Insight' "
    "section (when present) reflects the most recent AI Analyst conversation about this dataset, "
    "not a fresh analysis run at report time."
)
