# API Reference

Base URL: `/api/v1`. Interactive Swagger UI is available at `/docs` when the backend is running. All error responses share one shape:

```json
{ "error": { "code": "validation_error", "message": "...", "details": {} } }
```

Common error codes: `validation_error` (422), `not_found` (404), `unsupported_file` (415), `llm_not_configured` (503), `llm_call_failed` (502), `pdf_unavailable` (503), `internal_error` (500).

## Health

### `GET /health`
Returns app version, environment, whether the LLM is configured, and DB/storage status.

```bash
curl http://localhost:8000/api/v1/health
```
```json
{
  "status": "ok", "version": "0.1.0", "environment": "development", "llm_configured": false,
  "db": { "ok": true, "detail": null },
  "storage": { "backend": "local", "root": "/app/data", "writable": true }
}
```

## Datasets

### `POST /datasets/upload`
Multipart upload. Field name `file`. Validates extension (csv/xlsx/xls) and size (`MAX_UPLOAD_SIZE`), streams the upload in 1MB chunks so an oversized file is rejected before being fully buffered. On success, normalizes to a Parquet cache and infers coarse column types.

```bash
curl -X POST http://localhost:8000/api/v1/datasets/upload -F "file=@sales.csv"
```
Returns `201` with a `Dataset` object (`id`, `original_filename`, `row_count`, `column_count`, `status`, ...). `422` for empty/malformed files, `415` for a disallowed extension.

### `GET /datasets`
Lists all datasets, newest first.

### `GET /datasets/{id}`
Returns dataset metadata plus a coarse column list. `404` if not found.

### `GET /datasets/{id}/preview?page=&page_size=&sort=&sort_dir=&search=`
Paginated (default 50/page, max 500), sortable, and searchable row preview read from the Parquet cache.

### `GET /datasets/{id}/profile?refresh=false`
Full statistical profile: per-column stats, data-quality score breakdown, and detected issues. Cached after first computation; pass `refresh=true` to force recomputation.

### `GET /datasets/{id}/columns`
Full column detail including stats — reflects the profile's type refinement (e.g. a text column recognized as a date gets upgraded here after `/profile` has run once).

### `GET /datasets/{id}/eda-suggestions`
Auto-selected charts (already rendered as Plotly specs) based on the dataset's actual column types, each with a `reason` string. Returns an empty list rather than a meaningless chart when nothing fits.

### `DELETE /datasets/{id}`
Deletes the dataset row, its original file, and its Parquet cache. `204` on success.

## Analysis

### `POST /analysis/execute`
Deterministic filter → group-by/aggregate → sort → limit query. Persists the result under an `AnalysisSession` (auto-created if `session_id` omitted).

```json
{
  "dataset_id": "...",
  "filters": [{ "column": "region", "operator": "eq", "value": "West" }],
  "group_by": ["product"],
  "metrics": [{ "aggregation": "sum", "column": "revenue", "alias": "total" }],
  "sort": { "by": "total", "direction": "desc" },
  "limit": 10
}
```
Filter operators: `eq ne gt gte lt lte in not_in contains is_null not_null`. Aggregations: `sum mean median count min max std`.

### `POST /analysis/correlation`
Pearson/Spearman/Kendall correlation matrix over numeric columns (all, or a given subset). Flags pairs with |r| ≥ 0.7 as `strong_pairs`. `422` if fewer than 2 numeric columns are available.

### `POST /analysis/outliers`
IQR or Z-score outlier detection per numeric column, returning the actual top-20 most extreme full rows (not just indices).

### `POST /analysis/sql`
Read-only SQL over the dataset (exposed as a table named `dataset`). Only `SELECT`/`WITH...SELECT`, single statement, keyword-blocklisted against DDL/DML. `422` for anything else.

```json
{ "dataset_id": "...", "sql": "SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region ORDER BY total DESC LIMIT 5" }
```

### `POST /analysis/forecast`
Baseline forecasting (`naive | moving_average | linear | exponential_smoothing`) on a date column + numeric measure, auto-bucketed to daily/weekly/monthly based on span. Returns historical + forecast points and a backtest MAE. `422` if fewer than 5 historical periods are available after aggregation.

### `POST /analysis/chart`
Builds one Plotly-ready chart (`bar grouped_bar line area scatter histogram box heatmap pie`) from real query results. Persists under an `AnalysisSession` like `/execute`.

### `GET /analysis/sessions/{id}`
Returns a session and every result recorded under it (table/chart/sql/forecast), in order.

## AI

### `POST /ai/chat`
```json
{ "dataset_id": "...", "session_id": null, "message": "Which region made the most revenue?" }
```
Runs the tool-calling agent loop (up to 6 iterations). Returns the final assistant message, the full tool-call trace (name/arguments/result), and any charts the agent generated. `404` if the dataset doesn't exist; `503 llm_not_configured` if no LLM API key/model is set — checked *before* any session/message is persisted, so a misconfigured server never leaves orphaned chat state.

### `POST /ai/analyze`
Same as `/ai/chat` but sends a fixed "give me an executive summary" prompt — a convenience wrapper, not a different code path.

### `GET /ai/sessions/{id}/messages`
Full persisted message history for a chat session (user/assistant/tool rows).

## ML

### `POST /ml/suggest`
```json
{ "dataset_id": "..." }
```
Returns viable ML tasks (classification/regression/clustering/anomaly_detection) with suggested target/features and a `reason`. Returns an empty list on datasets under 20 rows rather than forcing a suggestion.

### `POST /ml/train`
```json
{
  "dataset_id": "...", "task": "classification", "target": "purchased",
  "features": ["age", "income", "region"], "algorithm": "random_forest"
}
```
Trains synchronously and returns full evaluation: metrics (task-appropriate — accuracy/precision/recall/F1/ROC-AUC for classification, MAE/MSE/RMSE/R² for regression, silhouette score for clustering, anomaly count/percentage for anomaly detection), a confusion matrix (classification), cluster sizes and centroids (clustering), sample flagged rows (anomaly detection), and feature importance. `422` for an unsuitable request (target with a single class, too few rows, target used as a feature, unsupported algorithm, ...).

Algorithms: classification `logistic_regression | random_forest`; regression `linear_regression | random_forest | gradient_boosting`; clustering is always `kmeans`; anomaly detection is always `isolation_forest`.

### `GET /ml/{model_id}/results`
Re-fetches a previously trained model's full result — identical shape to the `/train` response.

## Reports

### `POST /reports/generate`
```json
{ "dataset_id": "...", "format": "html" }
```
`format`: `html | pdf | json`. Gathers the real profile, quality score, up to 4 server-rendered charts, anomalies, deterministic recommendations, and (if a chat session exists for the dataset) the latest AI Analyst response — no LLM call happens during report generation itself. `pdf` returns `503 pdf_unavailable` with a clear message if WeasyPrint's system libraries aren't present in the environment (HTML/JSON are unaffected).

### `GET /reports/{id}`
Report metadata (format, sections included, timestamps).

### `GET /reports/{id}/download`
Streams the actual file (`text/html`, `application/pdf`, or `application/json`) with a `Content-Disposition: attachment` header.
