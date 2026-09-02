"""Unit tests for the deterministic profiling engine (no DB/HTTP)."""
from __future__ import annotations

import pandas as pd

from app.analytics.profiling import compute_profile


def _col(profile: dict, name: str) -> dict:
    return next(c for c in profile["columns"] if c["name"] == name)


def test_basic_shape_and_missing() -> None:
    df = pd.DataFrame({"a": [1, 2, None, 4], "b": ["x", "y", "z", "w"]})
    p = compute_profile(df)
    assert p["row_count"] == 4
    assert p["column_count"] == 2
    assert p["missing_cells"] == 1
    assert p["missing_percentage"] == round(100 * 1 / 8, 4)


def test_duplicate_rows_detected() -> None:
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    p = compute_profile(df)
    assert p["duplicate_rows"] == 1
    assert any(i["type"] == "duplicate_rows" for i in p["issues"])


def test_numeric_stats_correctness() -> None:
    df = pd.DataFrame({"n": [10, 20, 30, 40, 50]})
    p = compute_profile(df)
    n = _col(p, "n")["numeric"]
    assert n["count"] == 5
    assert n["mean"] == 30.0
    assert n["median"] == 30.0
    assert n["min"] == 10.0
    assert n["max"] == 50.0


def test_outlier_detection_iqr() -> None:
    # A single extreme value against a tight cluster should trip the IQR rule.
    values = [10, 11, 12, 11, 10, 12, 11, 10, 9999]
    df = pd.DataFrame({"n": values})
    p = compute_profile(df)
    n = _col(p, "n")["numeric"]
    assert n["outlier_count"] >= 1
    assert any(i["type"] == "extreme_outliers" and i["column"] == "n" for i in p["issues"])


def test_categorical_top_categories() -> None:
    df = pd.DataFrame({"region": ["West"] * 5 + ["East"] * 3 + ["South"] * 2})
    p = compute_profile(df)
    c = _col(p, "region")
    assert c["inferred_type"] == "categorical"
    assert c["categorical"]["top_categories"][0]["value"] == "West"
    assert c["categorical"]["top_categories"][0]["count"] == 5


def test_high_cardinality_categorical_flagged() -> None:
    # 60 distinct low-frequency values but ratio still <= 0.5 -> categorical, but high-cardinality issue.
    values = [f"cat_{i % 60}" for i in range(200)]
    df = pd.DataFrame({"tag": values})
    p = compute_profile(df)
    c = _col(p, "tag")
    assert c["inferred_type"] == "categorical"
    assert any(i["type"] == "high_cardinality_categorical" and i["column"] == "tag" for i in p["issues"])


def test_free_text_column_not_categorical() -> None:
    df = pd.DataFrame({"notes": [f"unique note number {i}" for i in range(20)]})
    p = compute_profile(df)
    c = _col(p, "notes")
    assert c["inferred_type"] == "text"
    assert c["logical_type"] == "freetext"


def test_fully_unique_short_token_column_is_identifier() -> None:
    # Unlike free-text sentences, short unique tokens (order refs) ARE identifiers.
    df = pd.DataFrame({"order_ref": [f"ORD-{i:04d}" for i in range(20)]})
    p = compute_profile(df)
    c = _col(p, "order_ref")
    assert c["logical_type"] == "identifier"
    assert any(i["type"] == "likely_identifier" and i["column"] == "order_ref" for i in p["issues"])


def test_datetime_detection_and_invalid_dates() -> None:
    values = ["2025-01-01", "2025-01-02", "2025-01-03", "not-a-date"] + [
        f"2025-02-{d:02d}" for d in range(1, 11)
    ]
    df = pd.DataFrame({"event_date": values})
    p = compute_profile(df)
    c = _col(p, "event_date")
    assert c["inferred_type"] == "datetime"
    assert c["datetime"]["invalid_count"] == 1
    assert any(i["type"] == "invalid_dates" and i["column"] == "event_date" for i in p["issues"])


def test_constant_column_flagged() -> None:
    df = pd.DataFrame({"status": ["active"] * 10, "n": range(10)})
    p = compute_profile(df)
    assert any(i["type"] == "constant_column" and i["column"] == "status" for i in p["issues"])


def test_identifier_column_flagged() -> None:
    df = pd.DataFrame({"id": [1, 2, 3, 4, 5], "n": [10, 20, 10, 20, 10]})
    p = compute_profile(df)
    c = _col(p, "id")
    assert c["logical_type"] == "identifier"
    assert any(i["type"] == "likely_identifier" and i["column"] == "id" for i in p["issues"])


def test_boolean_column() -> None:
    df = pd.DataFrame({"flag": [True, False, True, True, False]})
    p = compute_profile(df)
    c = _col(p, "flag")
    assert c["inferred_type"] == "boolean"
    assert c["boolean"]["true_count"] == 3
    assert c["boolean"]["false_count"] == 2


def test_missing_values_issue_threshold() -> None:
    # 40% missing should trip the >5% threshold.
    df = pd.DataFrame({"n": [1, 2, None, None, 5]})
    p = compute_profile(df)
    assert any(i["type"] == "missing_values" and i["column"] == "n" for i in p["issues"])


def test_quality_score_perfect_dataset() -> None:
    df = pd.DataFrame({"a": range(20), "b": [f"cat_{i % 3}" for i in range(20)]})
    p = compute_profile(df)
    q = p["quality"]
    assert q["completeness"] == 10.0
    assert q["duplicates"] == 10.0
    assert 0 <= q["overall"] <= 100


def test_quality_score_degrades_with_issues() -> None:
    good = pd.DataFrame({"a": range(20), "b": [f"cat_{i % 3}" for i in range(20)]})
    bad = pd.DataFrame({"a": [None] * 10 + list(range(10)), "b": [f"cat_{i % 3}" for i in range(20)]})
    q_good = compute_profile(good)["quality"]["overall"]
    q_bad = compute_profile(bad)["quality"]["overall"]
    assert q_bad < q_good


def test_empty_dataframe_does_not_crash() -> None:
    df = pd.DataFrame({"a": pd.Series(dtype="float64"), "b": pd.Series(dtype="object")})
    p = compute_profile(df)
    assert p["row_count"] == 0
    assert p["quality"]["overall"] >= 0


def test_skewness_none_for_small_samples() -> None:
    df = pd.DataFrame({"n": [1, 2]})
    p = compute_profile(df)
    assert _col(p, "n")["numeric"]["skewness"] is None
