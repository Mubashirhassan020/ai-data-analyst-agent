"""Baseline time-series forecasting: naive, moving-average, linear trend, and
exponential smoothing. Deterministic, explainable methods only — ARIMA-with-
automatic-order-selection is deliberately left out; it needs a fragile
stationarity/order-search step (and typically the `pmdarima` package) to do
responsibly, and a wrong auto-selected order is worse than an honest simple
baseline. Forecasting is refused outright when the series is too short to
fit any model meaningfully ("don't force forecasting on unsuitable data").

Every forecast ships with a backtest MAE (mean absolute error on held-out
recent periods) computed with the same method, so the caller gets an honest
sense of how far off the forecast might be — not just a bare number.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics.common import json_safe
from app.core.errors import ValidationError

MIN_HISTORICAL_PERIODS = 5
DEFAULT_PERIODS_AHEAD = 6
MAX_PERIODS_AHEAD = 24
BACKTEST_HOLDOUT = 3

METHODS = {"naive", "moving_average", "linear", "exponential_smoothing"}


def _granularity_for_span(span_days: float | None) -> str:
    if span_days is None or span_days <= 60:
        return "D"
    if span_days <= 730:
        return "W"
    return "M"


def _aggregate_series(
    df: pd.DataFrame, date_col: str, value_col: str, aggregation: str
) -> tuple[pd.Series, str]:
    dt = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    values = pd.to_numeric(df[value_col], errors="coerce")
    work = pd.DataFrame({"date": dt, "value": values}).dropna(subset=["date"])
    if work.empty:
        raise ValidationError(f"'{date_col}' has no parseable dates.")

    span_days = (work["date"].max() - work["date"].min()).days
    granularity = _granularity_for_span(span_days)
    bucketed = work["date"].dt.to_period(granularity).dt.start_time
    grouped = work.groupby(bucketed)["value"]
    series = (grouped.count() if aggregation == "count" else getattr(grouped, aggregation)()).sort_index()
    return series, granularity


def _fit_naive(y: np.ndarray, periods: int) -> np.ndarray:
    return np.full(periods, y[-1])


def _fit_moving_average(y: np.ndarray, periods: int, window: int = 3) -> np.ndarray:
    w = min(window, len(y))
    return np.full(periods, float(np.mean(y[-w:])))


def _fit_linear(y: np.ndarray, periods: int) -> np.ndarray:
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    future_x = np.arange(len(y), len(y) + periods)
    return slope * future_x + intercept


def _fit_exponential_smoothing(y: np.ndarray, periods: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import SimpleExpSmoothing

    model = SimpleExpSmoothing(y, initialization_method="estimated").fit()
    return np.asarray(model.forecast(periods))


_FITTERS = {
    "naive": _fit_naive,
    "moving_average": _fit_moving_average,
    "linear": _fit_linear,
    "exponential_smoothing": _fit_exponential_smoothing,
}

_FREQ_MAP = {"D": "D", "W": "W", "M": "MS"}


def _backtest_mae(y: np.ndarray, method: str) -> float | None:
    holdout = min(BACKTEST_HOLDOUT, max(0, len(y) - MIN_HISTORICAL_PERIODS))
    if holdout < 1:
        return None
    train, test = y[:-holdout], y[-holdout:]
    try:
        preds = _FITTERS[method](train, holdout)
    except Exception:  # noqa: BLE001 - backtest is best-effort, never blocks the main forecast
        return None
    return float(np.mean(np.abs(preds - test)))


def forecast(
    df: pd.DataFrame,
    *,
    date_column: str,
    value_column: str,
    periods_ahead: int = DEFAULT_PERIODS_AHEAD,
    method: str = "linear",
    aggregation: str = "sum",
) -> dict[str, Any]:
    if method not in METHODS:
        raise ValidationError(f"Unsupported forecasting method: {method!r}. Choose from {sorted(METHODS)}.")
    if date_column not in df.columns:
        raise ValidationError(f"Unknown column: {date_column!r}")
    if value_column not in df.columns:
        raise ValidationError(f"Unknown column: {value_column!r}")

    series, granularity = _aggregate_series(df, date_column, value_column, aggregation)
    if len(series) < MIN_HISTORICAL_PERIODS:
        raise ValidationError(
            f"Not enough historical data to forecast: {len(series)} period(s) found "
            f"after aggregating by {date_column!r}, at least {MIN_HISTORICAL_PERIODS} are required."
        )

    y = series.to_numpy(dtype=float)
    periods_ahead = max(1, min(periods_ahead, MAX_PERIODS_AHEAD))

    try:
        forecast_values = _FITTERS[method](y, periods_ahead)
    except Exception as e:
        raise ValidationError(f"Could not fit '{method}' model: {e}") from e

    backtest_mae = _backtest_mae(y, method)

    last_date = series.index[-1]
    future_index = pd.date_range(start=last_date, periods=periods_ahead + 1, freq=_FREQ_MAP[granularity])[1:]

    return {
        "method": method,
        "granularity": granularity,
        "date_column": date_column,
        "value_column": value_column,
        "historical": [{"date": json_safe(idx), "value": json_safe(v)} for idx, v in series.items()],
        "forecast": [
            {"date": json_safe(d), "value": json_safe(v)}
            for d, v in zip(future_index, forecast_values, strict=True)
        ],
        "backtest_mae": json_safe(backtest_mae),
        "historical_periods": int(len(series)),
    }
