"""Unit tests for Isolation Forest anomaly detection (no DB/HTTP)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.core.errors import ValidationError
from app.ml.anomaly import detect_anomalies


def _df_with_outliers() -> pd.DataFrame:
    rng = np.random.default_rng(9)
    normal = rng.normal(loc=[0, 0], scale=1.0, size=(95, 2))
    outliers = np.array([[50, 50], [-50, -50], [50, -50], [-50, 50], [60, 0]])
    data = np.vstack([normal, outliers])
    return pd.DataFrame({"a": data[:, 0], "b": data[:, 1]})


def test_detects_injected_outliers() -> None:
    df = _df_with_outliers()
    result = detect_anomalies(df, features=["a", "b"], contamination=0.05)
    assert result["metrics"]["anomaly_count"] >= 1
    sample_a_values = [r["a"] for r in result["sample_rows"]]
    assert any(abs(v) > 20 for v in sample_a_values)  # the injected extreme points are flagged


def test_sample_rows_include_all_original_columns() -> None:
    df = _df_with_outliers()
    df["label"] = "row"
    result = detect_anomalies(df, features=["a", "b"], contamination=0.05)
    assert all("label" in r for r in result["sample_rows"])


def test_non_numeric_feature_raises() -> None:
    df = pd.DataFrame({"a": range(20), "cat": ["x"] * 20})
    with pytest.raises(ValidationError):
        detect_anomalies(df, features=["a", "cat"])


def test_too_few_rows_raises() -> None:
    df = pd.DataFrame({"a": range(5), "b": range(5)})
    with pytest.raises(ValidationError):
        detect_anomalies(df, features=["a", "b"])


def test_unknown_feature_raises() -> None:
    df = _df_with_outliers()
    with pytest.raises(ValidationError):
        detect_anomalies(df, features=["nope"])
