"""Unit tests for the agent's tools, called directly (not through the LLM loop).
Each tool is a thin wrapper over an already-tested engine (Phases 4-6); these
tests confirm the wrapper correctly delegates against a real uploaded dataset."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.tools import ToolContext, get_tool_specs
from app.agents.tools.correlation_tool import correlation_tool
from app.agents.tools.forecast_tool import forecast_tool
from app.agents.tools.outlier_tool import outlier_tool
from app.agents.tools.pandas_tool import run_query_tool
from app.agents.tools.schema_tool import dataset_schema_tool
from app.agents.tools.sql_tool import sql_query_tool
from app.agents.tools.summary_tool import dataset_summary_tool
from app.agents.tools.viz_tool import visualization_tool
from app.db.session import session_factory
from app.main import app
from app.storage.factory import get_storage

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_sample() -> str:
    client = TestClient(app)
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    r = client.post("/api/v1/datasets/upload", files={"file": ("sample_sales.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _ctx(dataset_id: str) -> ToolContext:
    return ToolContext(db=session_factory(), storage=get_storage(), dataset_id=dataset_id)


def test_schema_tool_lists_real_columns() -> None:
    ds_id = _upload_sample()
    result = dataset_schema_tool.execute({}, _ctx(ds_id))
    assert result["row_count"] == 10
    assert result["column_count"] == 6
    names = {c["name"] for c in result["columns"]}
    assert names == {"order_id", "region", "product", "revenue", "units", "order_date"}


def test_summary_tool_returns_quality_and_stats() -> None:
    ds_id = _upload_sample()
    result = dataset_summary_tool.execute({}, _ctx(ds_id))
    assert result["row_count"] == 10
    assert "overall" in result["quality_score"]
    revenue_col = next(c for c in result["columns"] if c["name"] == "revenue")
    assert revenue_col["null_count"] == 1
    assert revenue_col["numeric"]["mean"] is not None


def test_run_query_tool_finds_highest_revenue_region() -> None:
    ds_id = _upload_sample()
    result = run_query_tool.execute(
        {
            "group_by": ["region"],
            "metrics": [{"aggregation": "sum", "column": "revenue", "alias": "total"}],
            "sort": {"by": "total", "direction": "desc"},
            "limit": 1,
        },
        _ctx(ds_id),
    )
    assert result["rows"][0]["region"] == "West"


def test_run_query_tool_surfaces_bad_column_as_exception() -> None:
    import pytest

    from app.core.errors import ValidationError

    ds_id = _upload_sample()
    with pytest.raises(ValidationError):
        run_query_tool.execute({"group_by": ["not_a_real_column"]}, _ctx(ds_id))


def test_correlation_tool() -> None:
    ds_id = _upload_sample()
    result = correlation_tool.execute({"columns": ["revenue", "units"]}, _ctx(ds_id))
    assert result["columns"] == ["revenue", "units"]
    assert result["matrix"][0][0] == 1.0


def test_outlier_tool() -> None:
    ds_id = _upload_sample()
    result = outlier_tool.execute({"columns": ["revenue"], "method": "iqr"}, _ctx(ds_id))
    assert result["columns"][0]["column"] == "revenue"
    assert result["columns"][0]["outlier_count"] >= 1


def test_visualization_tool_builds_real_chart() -> None:
    ds_id = _upload_sample()
    result = visualization_tool.execute(
        {"chart_type": "bar", "x": "region", "y": "revenue", "aggregation": "sum"}, _ctx(ds_id)
    )
    assert result["chart_type"] == "bar"
    assert result["data"][0]["type"] == "bar"


def test_sql_query_tool() -> None:
    ds_id = _upload_sample()
    result = sql_query_tool.execute(
        {"sql": "SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region ORDER BY total DESC LIMIT 1"},
        _ctx(ds_id),
    )
    assert result["rows"][0]["region"] == "West"


def test_forecast_tool() -> None:
    ds_id = _upload_sample()
    # sample_sales.csv only has 10 daily points; below the 5-period minimum is fine,
    # this just proves the tool wiring delegates correctly (engine behavior is
    # covered exhaustively in test_forecasting.py).
    result = forecast_tool.execute(
        {"date_column": "order_date", "value_column": "revenue", "method": "linear", "periods_ahead": 3},
        _ctx(ds_id),
    )
    assert result["method"] == "linear"
    assert len(result["forecast"]) == 3


def test_tool_specs_are_openai_function_format() -> None:
    specs = get_tool_specs()
    assert len(specs) == 8
    names = {s["function"]["name"] for s in specs}
    assert names == {
        "dataset_schema", "dataset_summary", "run_query", "sql_query",
        "correlation_analysis", "detect_outliers", "build_chart", "forecast",
    }
    for s in specs:
        assert s["type"] == "function"
        assert "parameters" in s["function"]
        assert s["function"]["parameters"]["type"] == "object"
