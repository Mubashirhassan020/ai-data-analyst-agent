from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.analytics.forecasting import forecast


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return forecast(
        ctx.dataframe(),
        date_column=args["date_column"],
        value_column=args["value_column"],
        periods_ahead=args.get("periods_ahead", 6),
        method=args.get("method", "linear"),
        aggregation=args.get("aggregation", "sum"),
    )


forecast_tool = Tool(
    name="forecast",
    description=(
        "Forecast future values of a numeric column over time, given a datetime column. "
        "Aggregates into daily/weekly/monthly periods automatically based on the date range, "
        "then fits a baseline model (naive, moving_average, linear, or exponential_smoothing). "
        "Returns both the historical series and the forecast, plus a backtest error (MAE) so "
        "you know how reliable the forecast is. Refuses to run if there isn't enough history "
        "(at least 5 periods) — say so plainly rather than forcing a forecast on it."
    ),
    parameters={
        "type": "object",
        "properties": {
            "date_column": {"type": "string"},
            "value_column": {"type": "string", "description": "Numeric column to forecast."},
            "periods_ahead": {"type": "integer", "minimum": 1, "maximum": 24, "description": "Default 6."},
            "method": {
                "type": "string",
                "enum": ["naive", "moving_average", "linear", "exponential_smoothing"],
                "description": "Default 'linear'.",
            },
            "aggregation": {
                "type": "string",
                "enum": ["sum", "mean", "median", "count", "min", "max", "std"],
                "description": "How to aggregate multiple rows per period. Default 'sum'.",
            },
        },
        "required": ["date_column", "value_column"],
    },
    execute=_execute,
)
