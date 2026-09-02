"""Unit tests for the deterministic query engine (no DB/HTTP)."""
from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.query import run_query
from app.core.errors import ValidationError


def _df() -> pd.DataFrame:
    return pd.DataFrame({
        "region": ["West", "East", "West", "South", "East", "West"],
        "product": ["A", "B", "A", "C", "B", "A"],
        "revenue": [100.0, 50.0, 200.0, 30.0, 60.0, 150.0],
        "units": [2, 1, 4, 1, 2, 3],
    })


def test_raw_passthrough_no_group_no_metrics() -> None:
    result = run_query(_df())
    assert result["row_count"] == 6
    assert result["total_matched_rows"] == 6
    assert result["truncated"] is False
    assert set(result["columns"]) == {"region", "product", "revenue", "units"}


def test_filter_eq() -> None:
    result = run_query(_df(), filters=[{"column": "region", "operator": "eq", "value": "West"}])
    assert result["row_count"] == 3
    assert all(r["region"] == "West" for r in result["rows"])


def test_filter_gt_numeric_coercion() -> None:
    result = run_query(_df(), filters=[{"column": "revenue", "operator": "gt", "value": "100"}])
    assert result["row_count"] == 2  # 200.0 and 150.0


def test_filter_gte_lt_lte_ne() -> None:
    # revenue = [100.0, 50.0, 200.0, 30.0, 60.0, 150.0]
    assert run_query(_df(), filters=[{"column": "revenue", "operator": "gte", "value": 150}])["row_count"] == 2  # 200, 150
    assert run_query(_df(), filters=[{"column": "revenue", "operator": "lt", "value": 100}])["row_count"] == 3  # 50, 30, 60
    assert run_query(_df(), filters=[{"column": "revenue", "operator": "lte", "value": 100}])["row_count"] == 4  # 100, 50, 30, 60
    assert run_query(_df(), filters=[{"column": "region", "operator": "ne", "value": "West"}])["row_count"] == 3


def test_filter_not_null() -> None:
    df = pd.DataFrame({"n": [1, None, 3]})
    result = run_query(df, filters=[{"column": "n", "operator": "not_null"}])
    assert result["row_count"] == 2


def test_filter_not_in() -> None:
    result = run_query(_df(), filters=[{"column": "region", "operator": "not_in", "value": ["East", "South"]}])
    assert result["row_count"] == 3  # all West rows


def test_filter_not_in_requires_list() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), filters=[{"column": "region", "operator": "not_in", "value": "West"}])


def test_filter_unsupported_operator_raises() -> None:
    # Not reachable through the API (Pydantic's FilterOperator Literal blocks it first),
    # but reachable via the agent's run_query tool, which passes raw LLM-supplied dicts
    # straight through without Pydantic validation — this is the real safety net for that.
    with pytest.raises(ValidationError):
        run_query(_df(), filters=[{"column": "revenue", "operator": "bogus", "value": 1}])


def test_date_filter_coercion_failure_raises() -> None:
    df = pd.DataFrame({"d": pd.to_datetime(["2025-01-01", "2025-01-02"])})
    with pytest.raises(ValidationError):
        run_query(df, filters=[{"column": "d", "operator": "eq", "value": "not-a-date"}])


def test_numeric_filter_coercion_failure_raises() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), filters=[{"column": "revenue", "operator": "gt", "value": "not-a-number"}])


def test_unsupported_aggregation_raises() -> None:
    # Same rationale as test_filter_unsupported_operator_raises: this guards the
    # tool-calling path, which bypasses Pydantic's Aggregation Literal validation.
    with pytest.raises(ValidationError):
        run_query(_df(), metrics=[{"aggregation": "bogus", "column": "revenue"}])


def test_aggregation_without_column_raises_with_group_by() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), group_by=["region"], metrics=[{"aggregation": "sum", "column": None}])


def test_aggregation_without_column_raises_without_group_by() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), metrics=[{"aggregation": "mean", "column": None}])


def test_filter_in() -> None:
    result = run_query(_df(), filters=[{"column": "region", "operator": "in", "value": ["East", "South"]}])
    assert result["row_count"] == 3


def test_filter_contains() -> None:
    result = run_query(_df(), filters=[{"column": "product", "operator": "contains", "value": "a"}])
    assert result["row_count"] == 3  # case-insensitive match on "A"


def test_filter_is_null() -> None:
    df = pd.DataFrame({"n": [1, None, 3]})
    result = run_query(df, filters=[{"column": "n", "operator": "is_null"}])
    assert result["row_count"] == 1


def test_filter_unknown_column_raises() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), filters=[{"column": "nope", "operator": "eq", "value": "x"}])


def test_filter_in_requires_list() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), filters=[{"column": "region", "operator": "in", "value": "West"}])


def test_group_by_sum_sorted_desc() -> None:
    result = run_query(
        _df(),
        group_by=["region"],
        metrics=[{"aggregation": "sum", "column": "revenue", "alias": "total_revenue"}],
        sort={"by": "total_revenue", "direction": "desc"},
    )
    assert result["rows"][0]["region"] == "West"
    assert result["rows"][0]["total_revenue"] == 450.0  # 100+200+150
    assert result["row_count"] == 3


def test_group_by_multiple_metrics() -> None:
    result = run_query(
        _df(),
        group_by=["region"],
        metrics=[
            {"aggregation": "sum", "column": "revenue", "alias": "total"},
            {"aggregation": "mean", "column": "revenue", "alias": "avg"},
            {"aggregation": "count", "column": "revenue", "alias": "n"},
        ],
    )
    west = next(r for r in result["rows"] if r["region"] == "West")
    assert west["total"] == 450.0
    assert west["avg"] == 150.0
    assert west["n"] == 3


def test_group_by_no_metrics_defaults_to_count() -> None:
    result = run_query(_df(), group_by=["region"])
    west = next(r for r in result["rows"] if r["region"] == "West")
    assert west["count"] == 3


def test_no_group_by_aggregate_single_row() -> None:
    result = run_query(_df(), metrics=[{"aggregation": "mean", "column": "revenue"}])
    assert result["row_count"] == 1
    assert result["rows"][0]["mean_revenue"] == pytest.approx(590.0 / 6)


def test_limit_truncates_and_flags() -> None:
    result = run_query(_df(), limit=2)
    assert result["row_count"] == 2
    assert result["total_matched_rows"] == 6
    assert result["truncated"] is True


def test_unknown_group_by_column_raises() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), group_by=["nope"], metrics=[{"aggregation": "count"}])


def test_unknown_metric_column_raises() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), metrics=[{"aggregation": "sum", "column": "nope"}])


def test_unknown_sort_column_raises() -> None:
    with pytest.raises(ValidationError):
        run_query(_df(), sort={"by": "nope"})


def test_default_raw_limit_applied() -> None:
    df = pd.DataFrame({"n": range(1500)})
    result = run_query(df)
    assert result["row_count"] == 1000
    assert result["truncated"] is True
