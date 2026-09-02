"""Unit tests for the read-only SQL engine (no DB/HTTP)."""
from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.sql_engine import run_sql
from app.core.errors import ValidationError


def _df() -> pd.DataFrame:
    return pd.DataFrame({
        "region": ["West", "East", "West", "South"],
        "revenue": [100.0, 50.0, 200.0, 30.0],
    })


def test_select_all() -> None:
    result = run_sql(_df(), "SELECT * FROM dataset")
    assert result["row_count"] == 4
    assert set(result["columns"]) == {"region", "revenue"}


def test_select_with_aggregation() -> None:
    result = run_sql(_df(), "SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region ORDER BY total DESC")
    assert result["rows"][0]["region"] == "West"
    assert result["rows"][0]["total"] == 300.0


def test_with_cte_allowed() -> None:
    sql = "WITH totals AS (SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region) SELECT * FROM totals ORDER BY total DESC LIMIT 1"
    result = run_sql(_df(), sql)
    assert result["rows"][0]["region"] == "West"


def test_trailing_semicolon_allowed() -> None:
    result = run_sql(_df(), "SELECT * FROM dataset;")
    assert result["row_count"] == 4


@pytest.mark.parametrize("sql", [
    "DROP TABLE dataset",
    "DELETE FROM dataset",
    "UPDATE dataset SET revenue = 0",
    "INSERT INTO dataset VALUES ('X', 1)",
    "ALTER TABLE dataset ADD COLUMN x INT",
    "TRUNCATE dataset",
    "CREATE TABLE evil (x INT)",
    "ATTACH 'evil.db' AS evil",
    "PRAGMA table_info(dataset)",
    "SELECT * FROM dataset; DROP TABLE dataset",
])
def test_dangerous_statements_rejected(sql: str) -> None:
    with pytest.raises(ValidationError):
        run_sql(_df(), sql)


def test_empty_query_rejected() -> None:
    with pytest.raises(ValidationError):
        run_sql(_df(), "")


def test_non_select_start_rejected() -> None:
    with pytest.raises(ValidationError):
        run_sql(_df(), "EXPLAIN SELECT * FROM dataset")


def test_invalid_sql_syntax_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        run_sql(_df(), "SELECT FROM WHERE")


def test_unknown_column_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        run_sql(_df(), "SELECT not_a_column FROM dataset")


def test_truncates_large_result() -> None:
    df = pd.DataFrame({"n": range(2000)})
    result = run_sql(df, "SELECT * FROM dataset")
    assert result["row_count"] == 1000
    assert result["total_matched_rows"] == 2000
    assert result["truncated"] is True


def test_column_named_like_keyword_is_rejected_defensively() -> None:
    # Documented trade-off: a column literally named 'delete' also gets blocked.
    df = pd.DataFrame({"delete": [1, 2, 3]})
    with pytest.raises(ValidationError):
        run_sql(df, "SELECT delete FROM dataset")
