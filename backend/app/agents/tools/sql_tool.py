from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext
from app.analytics.sql_engine import run_sql


def _execute(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return run_sql(ctx.dataframe(), args["sql"])


sql_query_tool = Tool(
    name="sql_query",
    description=(
        "Run a read-only SQL SELECT query against the dataset, exposed as a table named "
        "`dataset`, using real column names from dataset_schema. Use this for questions "
        "better expressed as SQL (joins-style window functions, complex CASE logic, nested "
        "aggregation) than a simple filter/group-by. Only SELECT/WITH queries are allowed — "
        "no INSERT/UPDATE/DELETE/DROP/ALTER or any statement that modifies data."
    ),
    parameters={
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A single read-only SELECT statement, e.g. \"SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region ORDER BY total DESC LIMIT 5\".",
            },
        },
        "required": ["sql"],
    },
    execute=_execute,
)
