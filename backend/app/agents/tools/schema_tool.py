from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.services.dataset_service import DatasetService


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    ds = DatasetService(ctx.db, ctx.storage).get(ctx.dataset_id)
    columns = [
        {
            "name": c.name,
            "inferred_type": c.inferred_type,
            "logical_type": c.logical_type,
            "null_count": c.null_count,
            "unique_count": c.unique_count,
        }
        for c in sorted(ds.columns, key=lambda c: c.position)
    ]
    return {"row_count": ds.row_count, "column_count": ds.column_count, "columns": columns}


dataset_schema_tool = Tool(
    name="dataset_schema",
    description=(
        "Get the dataset's columns, inferred types (integer/float/categorical/datetime/boolean/text), "
        "logical roles (identifier/measure/category/date/freetext), null counts, and unique counts. "
        "Call this first before answering any question about what data is available or which column to use."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
    execute=_execute,
)
