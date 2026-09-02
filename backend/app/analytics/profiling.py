"""Deterministic dataset profiling: types, statistics, quality score, issue detection.

Pure functions over a Pandas DataFrame. No DB/storage/LLM access here — this is the
computation layer the AI agent's tools call into later, so every number returned
must be reproducible from the dataframe alone.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from app.analytics.common import json_safe

# --- thresholds (documented because the numbers are otherwise arbitrary) ---

# A column is treated as datetime only if this fraction of its non-null values
# parse as dates — guards against numeric/text columns being misread as dates.
DATETIME_SUCCESS_THRESHOLD = 0.9

# Below this unique/non-null ratio, an object column is "categorical" rather
# than free text (e.g. region/product codes vs. free-form notes).
CATEGORICAL_MAX_RATIO = 0.5

# A "categorical" column with more distinct values than this is flagged as an
# issue — likely mis-typed (an identifier or free text) rather than a true category.
HIGH_CARDINALITY_ABS_THRESHOLD = 50

# Missing/outlier percentages above this are surfaced as dataset issues.
MISSING_ISSUE_THRESHOLD_PCT = 5.0
OUTLIER_ISSUE_THRESHOLD_PCT = 5.0

TOP_CATEGORIES_LIMIT = 10

# A fully-unique text column is only treated as an identifier if its values look
# like short tokens rather than sentences (average word count at or below this).
IDENTIFIER_MAX_AVG_WORDS = 2


def _pct(part: float, whole: float) -> float:
    return round(100.0 * part / whole, 4) if whole else 0.0


def _safe_ratio(part: float, whole: float) -> float:
    return (part / whole) if whole else 0.0


def _clip10(x: float) -> float:
    return max(0.0, min(10.0, x))


def _profile_numeric(s: pd.Series) -> dict[str, Any]:
    non_null = s.dropna()
    count = int(non_null.shape[0])
    if count == 0:
        return {
            "count": 0, "mean": None, "median": None, "std": None,
            "min": None, "max": None, "q1": None, "q3": None,
            "skewness": None, "outlier_count": 0, "outlier_percentage": 0.0,
        }
    q1, q3 = float(non_null.quantile(0.25)), float(non_null.quantile(0.75))
    iqr = q3 - q1
    if iqr > 0:
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outlier_mask = (non_null < lower) | (non_null > upper)
        outlier_count = int(outlier_mask.sum())
    else:
        outlier_count = 0
    skew = non_null.skew() if count >= 3 else None
    return {
        "count": count,
        "mean": json_safe(non_null.mean()),
        "median": json_safe(non_null.median()),
        "std": json_safe(non_null.std()) if count >= 2 else None,
        "min": json_safe(non_null.min()),
        "max": json_safe(non_null.max()),
        "q1": json_safe(q1),
        "q3": json_safe(q3),
        "skewness": json_safe(skew),
        "outlier_count": outlier_count,
        "outlier_percentage": _pct(outlier_count, count),
    }


def _profile_categorical(s: pd.Series) -> dict[str, Any]:
    non_null = s.dropna()
    count = int(non_null.shape[0])
    vc = non_null.value_counts().head(TOP_CATEGORIES_LIMIT)
    top = [
        {"value": str(idx), "count": int(cnt), "percentage": _pct(cnt, count)}
        for idx, cnt in vc.items()
    ]
    return {"distinct_count": int(non_null.nunique()), "top_categories": top}


def _profile_datetime(parsed: pd.Series, raw_non_null_count: int) -> dict[str, Any]:
    valid = parsed.dropna()
    invalid_count = raw_non_null_count - int(valid.shape[0])
    return {
        "min_date": json_safe(valid.min()) if not valid.empty else None,
        "max_date": json_safe(valid.max()) if not valid.empty else None,
        "range_days": (
            int((valid.max() - valid.min()).days) if not valid.empty else None
        ),
        "invalid_count": invalid_count,
        "invalid_percentage": _pct(invalid_count, raw_non_null_count),
    }


def _profile_boolean(s: pd.Series) -> dict[str, Any]:
    non_null = s.dropna()
    return {
        "true_count": int((non_null == True).sum()),  # noqa: E712
        "false_count": int((non_null == False).sum()),  # noqa: E712
    }


def _profile_column(name: str, s: pd.Series, row_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    null_count = int(s.isna().sum())
    non_null_count = row_count - null_count
    unique_count = int(s.nunique(dropna=True))

    numeric_block = categorical_block = datetime_block = boolean_block = None
    min_value = max_value = None

    if pd.api.types.is_bool_dtype(s):
        inferred_type = "boolean"
        logical_type = "flag"
        boolean_block = _profile_boolean(s)

    elif pd.api.types.is_integer_dtype(s) or pd.api.types.is_float_dtype(s):
        inferred_type = "integer" if pd.api.types.is_integer_dtype(s) else "float"
        numeric_block = _profile_numeric(s)
        min_value = str(numeric_block["min"]) if numeric_block["min"] is not None else None
        max_value = str(numeric_block["max"]) if numeric_block["max"] is not None else None
        is_identifier = unique_count == row_count and row_count > 1 and inferred_type == "integer"
        logical_type = "identifier" if is_identifier else "measure"
        if is_identifier:
            issues.append({
                "type": "likely_identifier", "column": name, "severity": "info",
                "message": f"'{name}' has a unique value per row — likely an identifier, not a measure.",
            })
        if numeric_block["outlier_percentage"] > OUTLIER_ISSUE_THRESHOLD_PCT:
            issues.append({
                "type": "extreme_outliers", "column": name, "severity": "medium",
                "message": (
                    f"'{name}' has {numeric_block['outlier_count']} outlier value(s) "
                    f"({numeric_block['outlier_percentage']}%) beyond 1.5x IQR."
                ),
            })

    elif pd.api.types.is_datetime64_any_dtype(s):
        inferred_type = "datetime"
        logical_type = "date"
        datetime_block = _profile_datetime(s, non_null_count)
        min_value, max_value = datetime_block["min_date"], datetime_block["max_date"]

    else:
        # object/text column: try datetime, then categorical vs. free text.
        parsed = pd.to_datetime(s, errors="coerce", format="mixed") if non_null_count else s
        success_ratio = _safe_ratio(int(parsed.notna().sum()), non_null_count)
        if non_null_count > 0 and success_ratio >= DATETIME_SUCCESS_THRESHOLD:
            inferred_type = "datetime"
            logical_type = "date"
            datetime_block = _profile_datetime(parsed, non_null_count)
            min_value, max_value = datetime_block["min_date"], datetime_block["max_date"]
            if datetime_block["invalid_count"] > 0:
                issues.append({
                    "type": "invalid_dates", "column": name, "severity": "low",
                    "message": (
                        f"'{name}' has {datetime_block['invalid_count']} value(s) "
                        f"that don't parse as dates."
                    ),
                })
        else:
            unique_ratio = _safe_ratio(unique_count, non_null_count)
            # Identifiers are short tokens ("CUST-0042"), not sentences — a fully-unique
            # free-text column (e.g. comments) shouldn't be mistaken for an ID column.
            non_null = s.dropna()
            avg_word_count = (
                non_null.astype(str).str.split().str.len().mean() if not non_null.empty else 0
            )
            is_identifier = (
                unique_count == row_count and row_count > 1 and avg_word_count <= IDENTIFIER_MAX_AVG_WORDS
            )
            if is_identifier:
                inferred_type, logical_type = "text", "identifier"
                issues.append({
                    "type": "likely_identifier", "column": name, "severity": "info",
                    "message": f"'{name}' has a unique value per row — likely an identifier.",
                })
            elif unique_ratio <= CATEGORICAL_MAX_RATIO:
                inferred_type, logical_type = "categorical", "category"
                categorical_block = _profile_categorical(s)
                if unique_count > HIGH_CARDINALITY_ABS_THRESHOLD:
                    issues.append({
                        "type": "high_cardinality_categorical", "column": name, "severity": "low",
                        "message": (
                            f"'{name}' has {unique_count} distinct categories — "
                            "consider treating it as text or grouping values."
                        ),
                    })
            else:
                inferred_type, logical_type = "text", "freetext"

    if unique_count <= 1 and non_null_count > 0:
        issues.append({
            "type": "constant_column", "column": name, "severity": "low",
            "message": f"'{name}' has a single distinct value across all rows.",
        })

    if null_count > 0:
        null_pct = _pct(null_count, row_count)
        if null_pct > MISSING_ISSUE_THRESHOLD_PCT:
            issues.append({
                "type": "missing_values", "column": name, "severity": "high" if null_pct > 50 else "medium",
                "message": f"'{name}' is missing {null_pct}% of values.",
            })

    profile = {
        "name": name,
        "inferred_type": inferred_type,
        "logical_type": logical_type,
        "null_count": null_count,
        "null_percentage": _pct(null_count, row_count),
        "unique_count": unique_count,
        "cardinality_ratio": round(_safe_ratio(unique_count, non_null_count), 4),
        "min_value": min_value,
        "max_value": max_value,
        "numeric": numeric_block,
        "categorical": categorical_block,
        "datetime": datetime_block,
        "boolean": boolean_block,
    }
    return profile, issues


def _compute_quality(
    *,
    row_count: int,
    column_count: int,
    missing_cells: int,
    duplicate_rows: int,
    columns: list[dict[str, Any]],
) -> dict[str, Any]:
    total_cells = row_count * column_count
    cols_with_missing = sum(1 for c in columns if c["null_count"] > 0)
    numeric_cols = [c for c in columns if c["numeric"] is not None]
    outlier_flagged = sum(
        1 for c in numeric_cols if c["numeric"]["outlier_percentage"] > OUTLIER_ISSUE_THRESHOLD_PCT
    )
    type_issue_cols = sum(
        1 for c in columns if c["datetime"] is not None and c["datetime"]["invalid_count"] > 0
    )

    completeness = _clip10(10 * (1 - _safe_ratio(missing_cells, total_cells)))
    missing_values = _clip10(10 * (1 - _safe_ratio(cols_with_missing, column_count)))
    duplicates = _clip10(10 * (1 - _safe_ratio(duplicate_rows, row_count)))
    data_types = _clip10(10 * (1 - _safe_ratio(type_issue_cols, column_count)))
    outliers = _clip10(10 * (1 - _safe_ratio(outlier_flagged, len(numeric_cols)))) if numeric_cols else 10.0

    overall = round((completeness + missing_values + duplicates + data_types + outliers) / 50 * 100)
    return {
        "overall": max(0, min(100, overall)),
        "completeness": round(completeness, 1),
        "missing_values": round(missing_values, 1),
        "duplicates": round(duplicates, 1),
        "data_types": round(data_types, 1),
        "outliers": round(outliers, 1),
    }


def compute_profile(df: pd.DataFrame) -> dict[str, Any]:
    """Compute the full structured profile for a dataframe. No side effects."""
    row_count, column_count = int(df.shape[0]), int(df.shape[1])
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    columns: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for pos, name in enumerate(df.columns):
        col_profile, col_issues = _profile_column(str(name), df[name], row_count)
        col_profile["position"] = pos
        columns.append(col_profile)
        issues.extend(col_issues)

    if duplicate_rows > 0:
        issues.append({
            "type": "duplicate_rows", "column": None, "severity": "medium" if duplicate_rows / max(row_count, 1) < 0.1 else "high",
            "message": f"{duplicate_rows} duplicate row(s) found ({_pct(duplicate_rows, row_count)}%).",
        })

    quality = _compute_quality(
        row_count=row_count,
        column_count=column_count,
        missing_cells=missing_cells,
        duplicate_rows=duplicate_rows,
        columns=columns,
    )

    return {
        "row_count": row_count,
        "column_count": column_count,
        "missing_cells": missing_cells,
        "missing_percentage": _pct(missing_cells, row_count * column_count),
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": _pct(duplicate_rows, row_count),
        "columns": columns,
        "issues": issues,
        "quality": quality,
        "generated_at": datetime.now(UTC).isoformat(),
    }
