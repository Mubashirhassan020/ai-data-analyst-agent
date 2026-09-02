from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.services.profiling_service import ProfilingService


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    profile = ProfilingService(ctx.db, ctx.storage).get_or_compute(ctx.dataset_id)
    return {
        "row_count": profile["row_count"],
        "column_count": profile["column_count"],
        "missing_cells": profile["missing_cells"],
        "missing_percentage": profile["missing_percentage"],
        "duplicate_rows": profile["duplicate_rows"],
        "columns": profile["columns"],
        "issues": profile["issues"],
        "quality_score": profile["quality"],
    }


dataset_summary_tool = Tool(
    name="dataset_summary",
    description=(
        "Get full descriptive statistics for every column (mean/median/std/quartiles for numeric, "
        "top categories for categorical, date ranges for datetime), a data-quality score breakdown, "
        "and a list of detected data-quality issues (missing values, duplicates, outliers, etc.). "
        "Use this for 'summarize this dataset' or 'what problems does this data have' questions."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
    execute=_execute,
)
