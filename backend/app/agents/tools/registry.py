"""The tool set available to the agent: schema inspection, descriptive statistics,
filtered/grouped queries, read-only SQL, correlation, outlier detection, chart
generation, and baseline forecasting — all thin wrappers over the already-tested
analytics engine (Phases 4-6, 9)."""
from __future__ import annotations

from app.agents.tools.base import Tool
from app.agents.tools.correlation_tool import correlation_tool
from app.agents.tools.forecast_tool import forecast_tool
from app.agents.tools.outlier_tool import outlier_tool
from app.agents.tools.pandas_tool import run_query_tool
from app.agents.tools.schema_tool import dataset_schema_tool
from app.agents.tools.sql_tool import sql_query_tool
from app.agents.tools.summary_tool import dataset_summary_tool
from app.agents.tools.viz_tool import visualization_tool

ALL_TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        dataset_schema_tool,
        dataset_summary_tool,
        run_query_tool,
        sql_query_tool,
        correlation_tool,
        outlier_tool,
        visualization_tool,
        forecast_tool,
    ]
}


def get_tool_specs() -> list[dict]:
    return [t.spec() for t in ALL_TOOLS.values()]
