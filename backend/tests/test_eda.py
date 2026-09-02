"""Unit tests for automated EDA chart suggestions."""
from __future__ import annotations

import pandas as pd

from app.analytics.eda import suggest_charts
from app.analytics.profiling import compute_profile


def test_no_datetime_no_line_suggestion() -> None:
    df = pd.DataFrame({"region": ["A", "B", "A", "C"] * 5, "revenue": range(20)})
    profile = compute_profile(df)
    suggestions = suggest_charts(df, profile)
    assert not any(s["chart_type"] == "line" for s in suggestions)


def test_datetime_and_measure_suggests_line() -> None:
    # Values must repeat, or a strictly-increasing column is all-unique and gets
    # classified as an identifier rather than a measure (see profiling.py).
    df = pd.DataFrame({
        "order_date": pd.date_range("2025-01-01", periods=20, freq="D"),
        "revenue": [i % 7 for i in range(20)],
    })
    profile = compute_profile(df)
    suggestions = suggest_charts(df, profile)
    assert any(s["chart_type"] == "line" for s in suggestions)


def test_single_numeric_column_no_heatmap() -> None:
    df = pd.DataFrame({"revenue": range(20), "region": ["A", "B"] * 10})
    profile = compute_profile(df)
    suggestions = suggest_charts(df, profile)
    assert not any(s["chart_type"] == "heatmap" for s in suggestions)


def test_two_numeric_columns_suggest_heatmap() -> None:
    df = pd.DataFrame({"revenue": [i % 7 for i in range(20)], "units": [i % 5 for i in range(20)]})
    profile = compute_profile(df)
    suggestions = suggest_charts(df, profile)
    assert any(s["chart_type"] == "heatmap" for s in suggestions)


def test_strongly_correlated_pair_suggests_scatter() -> None:
    revenue = [i % 10 for i in range(20)]
    df = pd.DataFrame({"revenue": revenue, "units": [v * 2 for v in revenue]})
    profile = compute_profile(df)
    suggestions = suggest_charts(df, profile)
    scatter = next((s for s in suggestions if s["chart_type"] == "scatter"), None)
    assert scatter is not None
    assert {scatter["x"], scatter["y"]} == {"revenue", "units"}


def test_identifier_columns_excluded_from_histograms() -> None:
    # "revenue" must have repeated values, or it too would be all-unique and
    # get classified as an identifier rather than a measure (correct behavior).
    df = pd.DataFrame({"id": range(20), "revenue": [i % 7 for i in range(20)]})
    profile = compute_profile(df)
    suggestions = suggest_charts(df, profile)
    histogram_cols = [s["x"] for s in suggestions if s["chart_type"] == "histogram"]
    assert "id" not in histogram_cols  # id is logical_type=identifier, not measure
    assert "revenue" in histogram_cols


def test_suggestions_capped() -> None:
    df = pd.DataFrame({
        "order_date": pd.date_range("2025-01-01", periods=30, freq="D"),
        **{f"measure_{i}": range(30) for i in range(5)},
        **{f"cat_{i}": (["a", "b", "c"] * 10) for i in range(5)},
    })
    profile = compute_profile(df)
    suggestions = suggest_charts(df, profile)
    assert len(suggestions) <= 8
