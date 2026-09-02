"""Unit tests for the baseline forecasting engine (no DB/HTTP)."""
from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.forecasting import forecast
from app.core.errors import ValidationError


def _trend_df(n: int = 20) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    values = [10.0 + 2.0 * i for i in range(n)]  # perfect linear trend, slope=2
    return pd.DataFrame({"date": dates, "revenue": values})


def test_linear_forecast_extrapolates_trend() -> None:
    df = _trend_df()
    result = forecast(df, date_column="date", value_column="revenue", method="linear", periods_ahead=3)
    assert result["method"] == "linear"
    assert result["historical_periods"] == 20
    # Last historical value is 10 + 2*19 = 48; next point should continue the trend (~50).
    assert result["forecast"][0]["value"] == pytest.approx(50.0, abs=0.5)
    assert len(result["forecast"]) == 3


def test_naive_forecast_repeats_last_value() -> None:
    df = _trend_df()
    result = forecast(df, date_column="date", value_column="revenue", method="naive", periods_ahead=2)
    last_historical = result["historical"][-1]["value"]
    assert all(p["value"] == pytest.approx(last_historical) for p in result["forecast"])


def test_moving_average_forecast_is_flat() -> None:
    df = _trend_df()
    result = forecast(df, date_column="date", value_column="revenue", method="moving_average", periods_ahead=3)
    values = [p["value"] for p in result["forecast"]]
    assert values[0] == values[1] == values[2]


def test_exponential_smoothing_runs_without_error() -> None:
    df = _trend_df()
    result = forecast(df, date_column="date", value_column="revenue", method="exponential_smoothing", periods_ahead=2)
    assert len(result["forecast"]) == 2
    assert all(p["value"] is not None for p in result["forecast"])


def test_backtest_mae_present_for_long_enough_series() -> None:
    df = _trend_df(n=20)
    result = forecast(df, date_column="date", value_column="revenue", method="linear")
    assert result["backtest_mae"] is not None
    assert result["backtest_mae"] < 5.0  # near-perfect linear trend should backtest well


def test_refuses_when_too_few_periods() -> None:
    df = _trend_df(n=3)
    with pytest.raises(ValidationError):
        forecast(df, date_column="date", value_column="revenue")


def test_unknown_date_column_raises() -> None:
    df = _trend_df()
    with pytest.raises(ValidationError):
        forecast(df, date_column="nope", value_column="revenue")


def test_unknown_value_column_raises() -> None:
    df = _trend_df()
    with pytest.raises(ValidationError):
        forecast(df, date_column="date", value_column="nope")


def test_unsupported_method_raises() -> None:
    df = _trend_df()
    with pytest.raises(ValidationError):
        forecast(df, date_column="date", value_column="revenue", method="arima")  # type: ignore[arg-type]


def test_periods_ahead_clamped() -> None:
    df = _trend_df()
    result = forecast(df, date_column="date", value_column="revenue", periods_ahead=999)
    assert len(result["forecast"]) == 24  # MAX_PERIODS_AHEAD


def test_aggregation_choice_affects_series() -> None:
    dates = pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-02", "2025-01-03", "2025-01-03", "2025-01-04", "2025-01-04", "2025-01-05", "2025-01-05"])
    values = [10, 20] * 5
    df = pd.DataFrame({"date": dates, "n": values})
    result = forecast(df, date_column="date", value_column="n", aggregation="sum", method="naive")
    assert result["historical"][0]["value"] == 30.0  # 10 + 20 on day 1


def test_weekly_granularity_for_longer_span() -> None:
    dates = pd.date_range("2025-01-01", periods=200, freq="D")
    df = pd.DataFrame({"date": dates, "n": range(200)})
    result = forecast(df, date_column="date", value_column="n", method="naive")
    assert result["granularity"] == "W"
