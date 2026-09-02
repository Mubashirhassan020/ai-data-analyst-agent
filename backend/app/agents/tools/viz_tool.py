from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.agents.tools.schemas import FILTER_SCHEMA
from app.analytics.charts import build_chart


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return build_chart(
        ctx.dataframe(),
        chart_type=args["chart_type"],
        x=args.get("x"),
        y=args.get("y"),
        aggregation=args.get("aggregation"),
        group_by=args.get("group_by"),
        columns=args.get("columns"),
        filters=args.get("filters") or [],
        title=args.get("title"),
    )


visualization_tool = Tool(
    name="build_chart",
    description=(
        "Generate a chart from the dataset: bar, grouped_bar, line, area, scatter, histogram, box, "
        "heatmap, or pie. Use this when the user asks to see, plot, chart, or visualize something. "
        "For time series use 'line' or 'area' with a datetime x column. For a correlation heatmap, "
        "pass `columns` (a list of numeric column names) instead of x/y."
    ),
    parameters={
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["bar", "grouped_bar", "line", "area", "scatter", "histogram", "box", "heatmap", "pie"],
            },
            "x": {"type": "string"},
            "y": {"type": "string"},
            "aggregation": {"type": "string", "enum": ["sum", "mean", "median", "count", "min", "max", "std"]},
            "group_by": {"type": "string"},
            "columns": {"type": "array", "items": {"type": "string"}, "description": "Heatmap only."},
            "filters": {"type": "array", "items": FILTER_SCHEMA},
            "title": {"type": "string"},
        },
        "required": ["chart_type"],
    },
    execute=_execute,
)
