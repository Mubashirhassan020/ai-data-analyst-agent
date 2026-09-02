# Architecture

## Overview

A modular monolith backend (FastAPI) behind a React SPA, with a clean separation between:

1. **The analytics engine** (`backend/app/analytics/`, `backend/app/ml/`) — pure functions over a Pandas DataFrame. No DB, storage, or LLM access. Every function raises a typed `ValidationError` on unsuitable input rather than producing a degenerate or misleading result.
2. **The service layer** (`backend/app/services/`) — orchestrates: load a dataset's dataframe, call an analytics function, persist the result, return it.
3. **The AI agent** (`backend/app/agents/`) — a tool-calling loop where the LLM decides *which* analytics function to call; it never computes a number itself.
4. **The API layer** (`backend/app/api/v1/`) — thin FastAPI routers that validate input via Pydantic and delegate to services.

This separation means every one of the analytics functions is independently unit-tested with hand-built DataFrames, with no need to spin up a database or mock an LLM — and the same functions back both the manual "Analysis Builder" UI and the AI agent's tools, so they can never disagree with each other.

## Request flow

```
Browser
  │  fetch()
  ▼
FastAPI router (app/api/v1/*.py)
  │  Pydantic validates the request body
  ▼
Service (app/services/*.py)
  │  loads DatasetService.load_dataframe() — reads the Parquet cache
  ▼
Analytics engine (app/analytics/*.py) or ML engine (app/ml/*.py)
  │  pure computation, raises ValidationError on unsuitable input
  ▼
Service persists the result (AnalysisResult / MLModel / Report row)
  │
  ▼
Pydantic response model → JSON
```

For the AI Analyst specifically:

```
POST /ai/chat
  │
  ▼
AgentService.chat()
  │  builds a system prompt with row/column counts only (not the schema itself —
  │  the model must call dataset_schema to see it, proving genuine tool use)
  ▼
LLM (OpenAI-compatible /chat/completions, tools=[...])
  │  returns either a final answer or one or more tool_calls
  ▼
Tool execution (app/agents/tools/*.py)
  │  each tool is a thin wrapper calling the SAME analytics engine functions
  │  used by the manual Analysis Builder — the LLM cannot get a different
  │  answer than a human clicking through the UI would
  ▼
Tool result fed back to the LLM as a `role: tool` message
  │  (large arrays are trimmed before this round-trip to keep context small;
  │  the frontend still receives the untrimmed result separately)
  ▼
LLM produces a final answer, or calls another tool (up to 6 iterations)
  │
  ▼
ChatMessage rows persisted; response returned with the full tool-call trace
```

## Database schema

PostgreSQL stores metadata only — dataset bytes and the Parquet cache live on the filesystem (via a swappable `Storage` interface, `app/storage/`).

```sql
users(id, email, created_at, updated_at)

datasets(
  id, user_id, original_filename, storage_key, parquet_key,
  file_size_bytes, mime_type, row_count, column_count,
  status,            -- uploaded | processing | ready | failed
  error_message, created_at, updated_at
)

dataset_columns(
  id, dataset_id, name, position,
  inferred_type,     -- integer | float | categorical | datetime | boolean | text
  logical_type,      -- identifier | measure | category | date | freetext | flag
  null_count, unique_count, min_value, max_value,
  stats              -- JSON: numeric/categorical/datetime/boolean sub-stats
)

dataset_profiles(
  id, dataset_id UNIQUE, summary (JSON, full profile snapshot),
  quality_score, issues (JSON array), generated_at
)

analysis_sessions(id, dataset_id, title, created_at, updated_at)

analysis_results(
  id, session_id, kind,   -- table | chart | sql | forecast
  spec (JSON, the request), result (JSON, the computed output),
  created_at, updated_at
)

chat_sessions(id, dataset_id, title, created_at, updated_at)

chat_messages(
  id, session_id, role,   -- user | assistant | tool
  content, tool_name, tool_args (JSON), tool_result (JSON),
  created_at, updated_at
)

ml_models(
  id, dataset_id, task,   -- classification | regression | clustering | anomaly_detection
  target, features (JSON), algorithm, params (JSON),
  metrics (JSON, scalar metrics only), result (JSON, full output —
  confusion matrix / feature importance / cluster sizes / etc.),
  artifact_key,           -- reserved; the fitted model object is not currently persisted
  status, created_at, updated_at
)

reports(
  id, dataset_id, format,  -- html | pdf | json
  storage_key, sections (JSON), created_at, updated_at
)
```

Migrations: `backend/alembic/versions/`. `0001_initial` creates all tables; `0002_ml_model_result` adds the `ml_models.result` column.

## Directory structure

See the [README's project structure section](../README.md#project-structure) for the top-level layout. Notable design points:

- `app/analytics/common.py` holds shared JSON-safety helpers (`json_safe`, `to_records`) used by every analytics module — numpy/pandas scalars (NaN, Timestamp, numpy int64) don't serialize to JSON directly, so this is centralized rather than duplicated per module (it was duplicated three times before being extracted).
- `app/agents/tools/` — each tool is a `Tool` dataclass (name, JSON-schema parameters, an `execute(args, ctx)` function) wrapping one analytics engine call. `ToolContext` carries the DB session, storage, and dataset ID, and lazily loads the dataframe once per chat turn even if multiple tools are called.
- `app/reports/chart_renderer.py` uses Matplotlib, not the Plotly specs from `app/analytics/charts.py` — WeasyPrint renders static HTML/CSS with no JavaScript execution, so Plotly's interactive output can't appear in a PDF. Converting Plotly JSON to a static image would need `kaleido`, which has known packaging/runtime fragility; re-rendering directly from the dataframe with Matplotlib was judged more robust, at the cost of some chart-building logic existing in two forms (interactive UI vs. static report).

## Key design decisions (and why)

| Decision | Reasoning |
|---|---|
| LLM never computes, only calls tools | The entire point of the project — see [README's anti-hallucination section](../README.md#ai-architecture--the-anti-hallucination-contract). |
| DuckDB for the SQL tool, not Postgres | The dataset is queried directly as an in-memory relation (`con.register("dataset", df)`) — no need to load user data into the metadata database, and DuckDB's SQL dialect is close enough to standard SQL for an LLM to write naturally. |
| SQL safety = single-statement + keyword blocklist | A full SQL parser is a large surface to get right; a blocklist of DDL/DML/session-control keywords, checked as whole tokens, is small, auditable, and rejects the categories of query this app should never run (see `app/analytics/sql_engine.py`). |
| Feature importance via native model signal, not SHAP | Gini importance / \|coefficient\| requires no extra dependency and is genuinely informative at this project's scale; SHAP is heavier and more fragile to install reliably. |
| No ARIMA in forecasting | Automatic order-selection needs additional tooling (`pmdarima`) and can silently produce a worse forecast than an honest simple baseline; every forecast instead ships with a backtest MAE so its reliability is visible rather than assumed. |
| Synchronous processing throughout | Profiling, ML training, and report generation all run in the request/response cycle rather than a background job queue — appropriate for the ~1M-row / 200MB target scale; documented as a scaling limitation for larger datasets. |
| Parquet cache on upload | CSV/XLSX parsing is comparatively slow; every downstream read (preview, profiling, analysis, AI tools, ML, reports) reads the same cached Parquet file instead of re-parsing the original upload. |
