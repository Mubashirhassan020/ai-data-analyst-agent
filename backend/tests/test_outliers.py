from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.outliers import detect_outliers
from app.core.errors import ValidationError


def test_iqr_detects_single_extreme_value() -> None:
    df = pd.DataFrame({"n": [10, 11, 12, 11, 10, 12, 11, 10, 9999]})
    result = detect_outliers(df, method="iqr")
    col = result["columns"][0]
    assert col["outlier_count"] == 1
    assert col["sample_rows"][0]["n"] == 9999


def test_zscore_detects_single_extreme_value() -> None:
    # Z-score uses mean/std computed FROM the same sample, so on a tiny n a single
    # extreme point inflates its own reference std enough to mask itself ("masking
    # effect" — a known limitation of non-robust z-score on small samples). Use a
    # large enough cluster that the outlier doesn't dominate the variance estimate.
    cluster = [10, 11, 12] * 10  # n=30
    df = pd.DataFrame({"n": cluster + [500]})
    result = detect_outliers(df, method="zscore")
    col = result["columns"][0]
    assert col["outlier_count"] >= 1
    assert any(r["n"] == 500 for r in col["sample_rows"])


def test_no_outliers_in_uniform_data() -> None:
    df = pd.DataFrame({"n": [10, 10, 10, 10, 10]})
    result = detect_outliers(df, method="iqr")
    assert result["columns"][0]["outlier_count"] == 0


def test_multiple_columns() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 1000], "b": [5, 5, 5, 5]})
    result = detect_outliers(df, method="iqr")
    names = {c["column"] for c in result["columns"]}
    assert names == {"a", "b"}


def test_column_selection() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 1000], "b": [5, 5, 5, 5]})
    result = detect_outliers(df, columns=["a"], method="iqr")
    assert [c["column"] for c in result["columns"]] == ["a"]


def test_non_numeric_column_raises() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "label": ["x", "y", "z"]})
    with pytest.raises(ValidationError):
        detect_outliers(df, columns=["label"])


def test_unsupported_method_raises() -> None:
    df = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(ValidationError):
        detect_outliers(df, method="bogus")


def test_sample_rows_include_full_row() -> None:
    # A 3-point sample is too small for IQR: quantile interpolation pulls q3 toward
    # the extreme value itself, "swallowing" it (same small-n artifact as z-score
    # masking above). Use enough points that the quartiles reflect the real cluster.
    values = [10, 11, 12, 11, 10, 12, 11, 10, 9999]
    labels = list("abcdefghi")
    df = pd.DataFrame({"n": values, "label": labels})
    result = detect_outliers(df, columns=["n"], method="iqr")
    sample = result["columns"][0]["sample_rows"][0]
    assert sample["n"] == 9999
    assert sample["label"] == "i"
