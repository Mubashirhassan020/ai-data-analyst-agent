from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analytics.correlation import compute_correlation
from app.core.errors import ValidationError


def test_perfect_positive_correlation() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 4, 6, 8, 10]})
    result = compute_correlation(df)
    assert result["matrix"][0][1] == pytest.approx(1.0)
    assert result["strong_pairs"][0]["correlation"] == pytest.approx(1.0)


def test_perfect_negative_correlation() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 8, 6, 4, 2]})
    result = compute_correlation(df)
    assert result["matrix"][0][1] == pytest.approx(-1.0)
    assert result["strong_pairs"][0]["correlation"] == pytest.approx(-1.0)


def test_weak_correlation_not_flagged_strong() -> None:
    # 5-point samples are too small to reliably produce a weak correlation by hand;
    # use a fixed-seed, independent (uncorrelated by construction) sample instead.
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"a": rng.normal(size=500), "b": rng.normal(size=500)})
    result = compute_correlation(df)
    assert abs(result["matrix"][0][1]) < 0.3
    assert result["strong_pairs"] == []


def test_ignores_non_numeric_columns() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "label": ["x", "y", "z"], "b": [3, 2, 1]})
    result = compute_correlation(df)
    assert set(result["columns"]) == {"a", "b"}


def test_column_selection() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [3, 2, 1], "c": [1, 1, 1]})
    result = compute_correlation(df, columns=["a", "b"])
    assert result["columns"] == ["a", "b"]


def test_requires_two_numeric_columns() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "label": ["x", "y", "z"]})
    with pytest.raises(ValidationError):
        compute_correlation(df)


def test_invalid_column_selection_raises() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [3, 2, 1]})
    with pytest.raises(ValidationError):
        compute_correlation(df, columns=["a", "nope"])
