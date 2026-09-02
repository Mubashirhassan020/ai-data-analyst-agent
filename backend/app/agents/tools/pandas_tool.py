from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.agents.tools.schemas import FILTER_SCHEMA, METRIC_SCHEMA
from app.analytics.query import run_query


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return run_query(
        ctx.dataframe(),
        filters=args.get("filters") or [],
        group_by=args.get("group_by") or [],
        metrics=args.get("metrics") or [],
        sort=args.get("sort"),
        limit=args.get("limit"),
    )


run_query_tool = Tool(
    name="run_query",
    description=(
        "Run a filter/group-by/aggregate query against the dataset using real column names from "
        "dataset_schema. Use this for questions like 'top 10 products by revenue', 'average order "
        "value', 'which region has the highest sales', or 'show transactions where region=West'. "
        "Leave group_by and metrics empty to get raw filtered rows (capped at 1000)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "filters": {"type": "array", "items": FILTER_SCHEMA, "description": "AND-combined filters."},
            "group_by": {"type": "array", "items": {"type": "string"}},
            "metrics": {"type": "array", "items": METRIC_SCHEMA},
            "sort": {
                "type": "object",
                "properties": {"by": {"type": "string"}, "direction": {"type": "string", "enum": ["asc", "desc"]}},
                "required": ["by"],
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 5000},
        },
        "required": [],
    },
    execute=_execute,
)
