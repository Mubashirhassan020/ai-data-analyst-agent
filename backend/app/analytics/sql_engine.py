"""Read-only SQL analysis over the dataset via an in-memory DuckDB connection.

Safety model: only SELECT (optionally WITH ... SELECT) queries are accepted;
a single statement only (no semicolon-chained follow-up query); and a
keyword blocklist rejects DDL/DML/session-control tokens (DROP, DELETE,
UPDATE, INSERT, ALTER, TRUNCATE, CREATE, ATTACH, PRAGMA, INSTALL, ...) even
if they appear inside a subquery. The dataset is exposed as a view named
`dataset` — the caller never sees or controls a file path.

The blocklist is a coarse token match, not a full SQL parser: a column or
alias literally named e.g. `delete` would also be rejected. That's an
accepted trade-off for a small, auditable safety surface over a bespoke
SQL-parsing security layer.
"""
from __future__ import annotations

import re
from typing import Any

import duckdb
import pandas as pd

from app.analytics.common import to_records
from app.core.errors import ValidationError

MAX_ROWS = 1000

_FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "attach", "detach", "copy", "export", "import", "pragma", "install",
    "load", "call", "set", "execute", "grant", "revoke", "replace",
    "vacuum", "checkpoint", "merge",
}
_ALLOWED_START = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _validate_query(sql: str) -> str:
    if not sql or not sql.strip():
        raise ValidationError("SQL query is empty.")
    stripped = sql.strip()
    body = stripped[:-1] if stripped.endswith(";") else stripped
    if ";" in body:
        raise ValidationError("Only a single SQL statement is allowed (no ';' chaining).")
    if not _ALLOWED_START.match(body):
        raise ValidationError("Only SELECT (or WITH ... SELECT) queries are allowed.")
    tokens = {t.lower() for t in _IDENTIFIER_RE.findall(body)}
    blocked = tokens & _FORBIDDEN_KEYWORDS
    if blocked:
        raise ValidationError(f"Query contains disallowed keyword(s): {sorted(blocked)}")
    return body


def run_sql(df: pd.DataFrame, sql: str) -> dict[str, Any]:
    query = _validate_query(sql)
    con = duckdb.connect(":memory:")
    try:
        con.register("dataset", df)
        try:
            result_df = con.execute(query).fetchdf()
        except duckdb.Error as e:
            raise ValidationError(f"SQL error: {e}") from e
    finally:
        con.close()

    total = int(result_df.shape[0])
    limited = result_df.head(MAX_ROWS)
    return {
        "columns": [str(c) for c in limited.columns],
        "rows": to_records(limited),
        "row_count": int(limited.shape[0]),
        "total_matched_rows": total,
        "truncated": total > MAX_ROWS,
        "sql": query,
    }
