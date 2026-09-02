"""Unit tests for the regression engine (no DB/HTTP)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.core.errors import ValidationError
from app.ml.regression import train_regressor


def _linear_df(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    x = rng.normal(0, 1, n)
    category = rng.choice(["A", "B"], n)
    y = 3.0 * x + rng.normal(0, 0.05, n)  # near-perfect linear relationship
    return pd.DataFrame({"x": x, "category": category, "y": y})


def test_linear_regression_fits_near_perfect_trend() -> None:
    df = _linear_df()
    result = train_regressor(df, target="y", features=["x", "category"], algorithm="linear_regression")
    assert result["metrics"]["r2"] > 0.95


def test_random_forest_regressor_runs() -> None:
    df = _linear_df()
    result = train_regressor(df, target="y", features=["x", "category"], algorithm="random_forest")
    assert result["algorithm"] == "random_forest"
    assert "rmse" in result["metrics"]


def test_gradient_boosting_regressor_runs() -> None:
    df = _linear_df()
    result = train_regressor(df, target="y", features=["x"], algorithm="gradient_boosting")
    assert result["algorithm"] == "gradient_boosting"


def test_rmse_is_sqrt_of_mse() -> None:
    df = _linear_df()
    result = train_regressor(df, target="y", features=["x"])
    m = result["metrics"]
    # Both values are independently rounded to 4dp in the result, so compare with
    # an absolute tolerance that accounts for that double-rounding, not a tight
    # relative one against the already-rounded mse.
    assert m["rmse"] == pytest.approx(m["mse"] ** 0.5, abs=1e-3)


def test_non_numeric_target_raises() -> None:
    df = _linear_df()
    with pytest.raises(ValidationError):
        train_regressor(df, target="category", features=["x"])


def test_constant_target_raises() -> None:
    df = pd.DataFrame({"x": range(20), "y": [5.0] * 20})
    with pytest.raises(ValidationError):
        train_regressor(df, target="y", features=["x"])


def test_unknown_column_raises() -> None:
    df = _linear_df()
    with pytest.raises(ValidationError):
        train_regressor(df, target="y", features=["nope"])


def test_too_few_rows_raises() -> None:
    df = pd.DataFrame({"x": range(5), "y": [1.0, 2.0, 3.0, 4.0, 5.0]})
    with pytest.raises(ValidationError):
        train_regressor(df, target="y", features=["x"])


def test_feature_importance_identifies_dominant_feature() -> None:
    rng = np.random.default_rng(3)
    n = 100
    strong = rng.normal(0, 1, n)
    weak = rng.normal(0, 1, n)
    y = 10.0 * strong + 0.01 * weak
    df = pd.DataFrame({"strong": strong, "weak": weak, "y": y})
    result = train_regressor(df, target="y", features=["strong", "weak"], algorithm="random_forest")
    top = result["feature_importance"][0]
    assert top["feature"] == "strong"
