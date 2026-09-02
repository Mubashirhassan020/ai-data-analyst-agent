from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.analytics.outliers import detect_outliers


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return detect_outliers(ctx.dataframe(), columns=args.get("columns"), method=args.get("method", "iqr"))


outlier_tool = Tool(
    name="detect_outliers",
    description=(
        "Detect unusual/anomalous values in numeric columns using the IQR or Z-score method, and "
        "return the actual outlier rows. Use this for 'are there any unusual transactions' or "
        "'find anomalies' questions. Omit `columns` to check all numeric columns."
    ),
    parameters={
        "type": "object",
        "properties": {
            "columns": {"type": "array", "items": {"type": "string"}},
            "method": {"type": "string", "enum": ["iqr", "zscore"]},
        },
        "required": [],
    },
    execute=_execute,
)
