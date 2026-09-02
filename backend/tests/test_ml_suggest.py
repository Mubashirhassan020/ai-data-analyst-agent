"""Unit tests for ML task suggestions, driven by real profiles from compute_profile."""
from __future__ import annotations

import pandas as pd

from app.analytics.profiling import compute_profile
from app.ml.suggest import MIN_ROWS_FOR_ML, suggest_ml_tasks


def test_too_few_rows_yields_no_suggestions() -> None:
    df = pd.DataFrame({"a": range(5), "b": ["x", "y"] * 2 + ["x"]})
    profile = compute_profile(df)
    assert suggest_ml_tasks(profile) == []


def test_balanced_categorical_target_suggested_for_classification() -> None:
    n = MIN_ROWS_FOR_ML + 10
    df = pd.DataFrame({
        "label": (["yes", "no"] * (n // 2))[:n],
        "score": [i % 7 for i in range(n)],
    })
    profile = compute_profile(df)
    suggestions = suggest_ml_tasks(profile)
    class_suggestions = [s for s in suggestions if s["task"] == "classification"]
    assert any(s["target"] == "label" for s in class_suggestions)


def test_boolean_target_suggested_for_classification() -> None:
    # profiling.py types booleans separately from "categorical" (see
    # _profile_boolean) — the suggestion engine must handle both branches.
    n = MIN_ROWS_FOR_ML + 10
    df = pd.DataFrame({
        "purchased": ([True, False] * (n // 2))[:n],
        "income": [1000 + (i % 7) * 500 for i in range(n)],  # repeated values -> a measure, not an identifier
    })
    profile = compute_profile(df)
    assert next(c for c in profile["columns"] if c["name"] == "purchased")["inferred_type"] == "boolean"
    suggestions = suggest_ml_tasks(profile)
    assert any(s["task"] == "classification" and s["target"] == "purchased" for s in suggestions)


def test_rare_class_not_suggested() -> None:
    n = MIN_ROWS_FOR_ML + 10
    labels = ["common"] * (n - 1) + ["rare"]
    df = pd.DataFrame({"label": labels, "score": [i % 7 for i in range(n)]})
    profile = compute_profile(df)
    suggestions = suggest_ml_tasks(profile)
    assert not any(s["task"] == "classification" and s["target"] == "label" for s in suggestions)


def test_numeric_measure_suggested_for_regression() -> None:
    n = MIN_ROWS_FOR_ML + 10
    df = pd.DataFrame({"revenue": [i % 13 for i in range(n)], "units": [i % 5 for i in range(n)]})
    profile = compute_profile(df)
    suggestions = suggest_ml_tasks(profile)
    regression_targets = {s["target"] for s in suggestions if s["task"] == "regression"}
    assert "revenue" in regression_targets
    assert "units" in regression_targets


def test_two_measures_suggest_clustering_and_anomaly() -> None:
    n = MIN_ROWS_FOR_ML + 10
    df = pd.DataFrame({"a": [i % 11 for i in range(n)], "b": [i % 9 for i in range(n)]})
    profile = compute_profile(df)
    suggestions = suggest_ml_tasks(profile)
    tasks = {s["task"] for s in suggestions}
    assert "clustering" in tasks
    assert "anomaly_detection" in tasks


def test_single_measure_no_clustering() -> None:
    n = MIN_ROWS_FOR_ML + 10
    df = pd.DataFrame({"a": [i % 11 for i in range(n)], "cat": ["x", "y"] * (n // 2)})
    profile = compute_profile(df)
    suggestions = suggest_ml_tasks(profile)
    assert not any(s["task"] == "clustering" for s in suggestions)
    assert any(s["task"] == "anomaly_detection" for s in suggestions)


def test_suggestions_capped_at_eight() -> None:
    n = MIN_ROWS_FOR_ML + 10
    data = {f"measure_{i}": [j % 13 for j in range(n)] for i in range(6)}
    data["cat"] = (["a", "b"] * (n // 2))
    df = pd.DataFrame(data)
    profile = compute_profile(df)
    assert len(suggest_ml_tasks(profile)) <= 8
