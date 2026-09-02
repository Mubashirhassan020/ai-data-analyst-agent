from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.analytics.correlation import compute_correlation


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return compute_correlation(ctx.dataframe(), columns=args.get("columns"), method=args.get("method", "pearson"))


correlation_tool = Tool(
    name="correlation_analysis",
    description=(
        "Compute the correlation matrix between numeric columns and list strongly correlated pairs "
        "(|r| >= 0.7). Use this for 'which variables are correlated' or 'relationship between X and Y' "
        "questions. Omit `columns` to use all numeric columns."
    ),
    parameters={
        "type": "object",
        "properties": {
            "columns": {"type": "array", "items": {"type": "string"}},
            "method": {"type": "string", "enum": ["pearson", "spearman", "kendall"]},
        },
        "required": [],
    },
    execute=_execute,
)
