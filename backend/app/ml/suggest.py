"""Suggests viable ML tasks from a computed profile — same philosophy as the
EDA chart suggestions (Phase 6): don't force training on unsuitable data, and
explain why each suggestion was made. A "suggestion" is a hint, not a
guarantee — /ml/train independently re-validates suitability with the real
data before ever fitting a model.
"""
from __future__ import annotations

from typing import Any

MIN_ROWS_FOR_ML = 20
MAX_CLASSES_FOR_CLASSIFICATION = 20
MIN_CLASS_COUNT = 2
MAX_SUGGESTIONS = 8
MAX_FEATURES_SUGGESTED = 10


def suggest_ml_tasks(profile: dict[str, Any]) -> list[dict[str, Any]]:
    row_count = profile["row_count"]
    if row_count < MIN_ROWS_FOR_ML:
        return []

    columns = profile["columns"]
    numeric_measures = [
        c["name"] for c in columns if c["inferred_type"] in ("integer", "float") and c["logical_type"] == "measure"
    ]
    usable_feature_pool = [c["name"] for c in columns if c["logical_type"] in ("measure", "category")]

    suggestions: list[dict[str, Any]] = []

    for c in columns:
        if c["inferred_type"] == "categorical":
            if not (2 <= c["unique_count"] <= MAX_CLASSES_FOR_CLASSIFICATION):
                continue
            cat_stats = c.get("categorical")
            if not cat_stats or not cat_stats.get("top_categories"):
                continue
            min_seen_count = min(tc["count"] for tc in cat_stats["top_categories"])
            if min_seen_count < MIN_CLASS_COUNT:
                continue
        elif c["inferred_type"] == "boolean":
            # Booleans are always exactly 2 classes — a natural, common classification
            # target (e.g. "purchased", "churned") that the categorical branch above
            # doesn't cover, since profiling.py types them separately.
            bool_stats = c.get("boolean")
            if not bool_stats:
                continue
            if bool_stats["true_count"] < MIN_CLASS_COUNT or bool_stats["false_count"] < MIN_CLASS_COUNT:
                continue
        else:
            continue

        features = [f for f in usable_feature_pool if f != c["name"]][:MAX_FEATURES_SUGGESTED]
        if not features:
            continue
        suggestions.append({
            "task": "classification",
            "target": c["name"],
            "features": features,
            "reason": f"'{c['name']}' is categorical with {c['unique_count']} classes — a classifier could predict it from the other columns.",
        })

    for name in numeric_measures:
        features = [f for f in usable_feature_pool if f != name][:MAX_FEATURES_SUGGESTED]
        if not features:
            continue
        suggestions.append({
            "task": "regression",
            "target": name,
            "features": features,
            "reason": f"'{name}' is a numeric measure — a regressor could predict it from the other columns.",
        })

    if len(numeric_measures) >= 2:
        suggestions.append({
            "task": "clustering",
            "target": None,
            "features": numeric_measures[:8],
            "reason": f"{len(numeric_measures)} numeric measures are present — clustering could reveal natural groupings.",
        })

    if numeric_measures:
        suggestions.append({
            "task": "anomaly_detection",
            "target": None,
            "features": numeric_measures[:8],
            "reason": "Numeric measures are present — Isolation Forest can flag multivariate outliers.",
        })

    return suggestions[:MAX_SUGGESTIONS]
