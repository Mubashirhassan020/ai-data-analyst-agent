"""Unit tests for the chart-spec builder (no DB/HTTP)."""
from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.charts import build_chart
from app.core.errors import ValidationError


def _df() -> pd.DataFrame:
    return pd.DataFrame({
        "region": ["West", "East", "West", "South", "East", "West"],
        "product": ["A", "B", "A", "C", "B", "A"],
        "revenue": [100.0, 50.0, 200.0, 30.0, 60.0, 150.0],
        "units": [2, 1, 4, 1, 2, 3],
        "order_date": pd.to_datetime([
            "2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05", "2025-01-06",
        ]),
    })


def test_histogram_basic() -> None:
    result = build_chart(_df(), chart_type="histogram", x="revenue")
    assert result["chart_type"] == "histogram"
    assert result["data"][0]["type"] == "histogram"
    assert result["row_count"] == 6


def test_histogram_requires_numeric_column() -> None:
    with pytest.raises(ValidationError):
        build_chart(_df(), chart_type="histogram", x="region")


def test_box_grouped_by_category() -> None:
    result = build_chart(_df(), chart_type="box", x="region", y="revenue")
    names = {t["name"] for t in result["data"]}
    assert names == {"West", "East", "South"}


def test_box_ungrouped() -> None:
    result = build_chart(_df(), chart_type="box", y="revenue")
    assert len(result["data"]) == 1
    assert result["data"][0]["y"]


def test_bar_aggregates_by_sum() -> None:
    result = build_chart(_df(), chart_type="bar", x="region", y="revenue", aggregation="sum")
    trace = result["data"][0]
    west_idx = trace["x"].index("West")
    assert trace["y"][west_idx] == 450.0  # 100+200+150


def test_bar_defaults_to_count_without_y() -> None:
    result = build_chart(_df(), chart_type="bar", x="region")
    trace = result["data"][0]
    west_idx = trace["x"].index("West")
    assert trace["y"][west_idx] == 3


def test_grouped_bar_requires_group_by() -> None:
    with pytest.raises(ValidationError):
        build_chart(_df(), chart_type="grouped_bar", x="region", y="revenue")


def test_grouped_bar_produces_multiple_traces() -> None:
    result = build_chart(_df(), chart_type="grouped_bar", x="region", y="revenue", group_by="product")
    assert len(result["data"]) >= 2
    assert result["layout"]["barmode"] == "group"


def test_pie_rejects_group_by() -> None:
    with pytest.raises(ValidationError):
        build_chart(_df(), chart_type="pie", x="region", group_by="product")


def test_pie_basic() -> None:
    result = build_chart(_df(), chart_type="pie", x="region", y="revenue", aggregation="sum")
    trace = result["data"][0]
    assert trace["type"] == "pie"
    assert set(trace["labels"]) == {"West", "East", "South"}


def test_pie_caps_slices_with_other() -> None:
    df = pd.DataFrame({"cat": [f"c{i}" for i in range(15)], "val": range(15)})
    result = build_chart(df, chart_type="pie", x="cat", y="val", aggregation="sum")
    trace = result["data"][0]
    assert len(trace["labels"]) <= 8
    assert "Other" in trace["labels"]


def test_line_time_series() -> None:
    result = build_chart(_df(), chart_type="line", x="order_date", y="revenue", aggregation="sum")
    assert result["chart_type"] == "line"
    assert result["granularity"] == "D"
    assert sum(result["data"][0]["y"]) == 590.0


def test_area_sets_fill() -> None:
    result = build_chart(_df(), chart_type="area", x="order_date", y="revenue")
    assert result["data"][0]["fill"] == "tozeroy"


def test_line_rejects_unparseable_dates() -> None:
    df = pd.DataFrame({"x": ["not", "a", "date"], "y": [1, 2, 3]})
    with pytest.raises(ValidationError):
        build_chart(df, chart_type="line", x="x", y="y")


def test_scatter_basic() -> None:
    result = build_chart(_df(), chart_type="scatter", x="revenue", y="units")
    trace = result["data"][0]
    assert trace["type"] == "scatter"
    assert trace["mode"] == "markers"
    assert len(trace["x"]) == 6


def test_scatter_requires_numeric_columns() -> None:
    with pytest.raises(ValidationError):
        build_chart(_df(), chart_type="scatter", x="region", y="revenue")


def test_heatmap_correlation() -> None:
    result = build_chart(_df(), chart_type="heatmap", columns=["revenue", "units"])
    trace = result["data"][0]
    assert trace["type"] == "heatmap"
    assert trace["x"] == ["revenue", "units"]
    assert trace["z"][0][0] == 1.0


def test_unsupported_chart_type_raises() -> None:
    with pytest.raises(ValidationError):
        build_chart(_df(), chart_type="bogus", x="region")


def test_filters_applied_before_charting() -> None:
    result = build_chart(
        _df(), chart_type="bar", x="region", y="revenue",
        filters=[{"column": "region", "operator": "eq", "value": "West"}],
    )
    trace = result["data"][0]
    assert trace["x"] == ["West"]


def test_empty_after_filters_raises() -> None:
    with pytest.raises(ValidationError):
        build_chart(
            _df(), chart_type="bar", x="region",
            filters=[{"column": "region", "operator": "eq", "value": "Nowhere"}],
        )


def test_box_too_many_groups_raises() -> None:
    df = pd.DataFrame({"cat": [f"c{i}" for i in range(20)], "val": range(20)})
    with pytest.raises(ValidationError):
        build_chart(df, chart_type="box", x="cat", y="val")
