# AI Data Analyst Agent

An end-to-end AI-powered data analytics platform. Upload a CSV or Excel dataset, get automated profiling and data-quality scoring, explore auto-generated visualizations, run manual analysis without any AI involved, train ML models, generate exportable reports, and chat with a **tool-using AI analyst** that answers questions with real computations — never invented numbers.

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![React](https://img.shields.io/badge/react-18-61dafb)
![License](https://img.shields.io/badge/license-MIT-green)

> Replace `OWNER/REPO` in the badge URL above once this repo is pushed to GitHub.

## Table of contents

- [Problem statement](#problem-statement)
- [Features](#features)
- [Architecture](#architecture)
- [AI architecture — the anti-hallucination contract](#ai-architecture--the-anti-hallucination-contract)
- [Tech stack](#tech-stack)
- [Screenshots / demo](#screenshots--demo)
- [Quick start (Docker)](#quick-start-docker)
- [Local development](#local-development)
- [Environment configuration](#environment-configuration)
- [Testing](#testing)
- [Project structure](#project-structure)
- [API documentation](#api-documentation)
- [Example questions and results](#example-questions-and-results)
- [Limitations](#limitations)
- [Future improvements](#future-improvements)
- [License](#license)

## Problem statement

Most "chat with your data" demos let an LLM guess numeric answers directly from a prompt — it has seen a few rows, so it *sounds* plausible, but the numbers are fabricated. That's fine for a toy, useless for anything a business would actually rely on.

This project inverts the design: **the LLM never computes anything.** It decides *which* deterministic tool to call (a Pandas aggregation, a correlation matrix, an outlier scan, a SQL query, a forecast), that tool runs against the real uploaded data, and the LLM's job is limited to explaining a result it was handed. Every numeric claim in a chat response is traceable to an actual tool call — visible in the UI as an expandable trace.

## Features

- **Upload & validate** — CSV/XLSX/XLS, size and type validation, encoding detection, normalized to a Parquet cache for fast repeat access.
- **Automated profiling** — per-column type inference (integer/float/categorical/datetime/boolean/text), descriptive statistics, a 5-signal data-quality score (completeness, missing values, duplicates, data types, outliers), and a list of detected issues (missing values, duplicate rows, constant columns, high-cardinality categoricals, outliers, invalid dates).
- **Automated EDA** — chart-type selection based on actual column types (histograms for numeric measures, bar charts for categoricals, line charts for time series, a correlation heatmap and scatter plot for related numeric pairs) — never a meaningless chart.
- **Manual Analysis Builder** — pick a chart type, X/Y columns, aggregation, group-by, and filters without touching the AI at all.
- **Tool-using AI Analyst** — a chat interface where the model calls real tools: dataset schema, descriptive statistics, filtered/grouped queries, read-only SQL (DuckDB, blocklisted against DDL/DML), correlation, outlier detection (IQR/Z-score), chart generation, and baseline forecasting (naive/moving-average/linear/exponential-smoothing with a backtest error).
- **Machine learning** — classification (Logistic Regression, Random Forest), regression (Linear Regression, Random Forest, Gradient Boosting), clustering (K-Means), and anomaly detection (Isolation Forest) — with a suggestion engine that refuses to force training on unsuitable data, plus native feature-importance explanations.
- **Reports** — HTML, PDF, and JSON export combining the real profile, real charts (rendered server-side), real anomalies, deterministic recommendations, and (when available) the most recent AI Analyst conversation about the dataset.
- **Every UI state handled** — loading, empty, error-with-retry, upload progress — not just the happy path.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                React SPA (Vite + TypeScript)                 │
│  Landing · Dashboard · Datasets · AI Analyst · Reports        │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST / JSON
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ API Layer (routers): datasets, analysis, ai, ml, reports│ │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Services: Dataset · Profiling · Analytics · Viz ·      │  │
│  │           ML · Report                                   │ │
│  ├───────────────────────────────────────────────────────┤  │
│  │ AI Agent: LLM client + tool router                     │  │
│  │  Tools: schema, summary, pandas query, SQL (DuckDB),   │  │
│  │         correlation, outliers, chart, forecast          │ │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Analytics engine (pure functions, no DB/LLM access):    │ │
│  │  profiling · query · correlation · outliers · charts ·  │ │
│  │  sql_engine · forecasting                                │ │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Data Access (SQLAlchemy) · Storage (local FS, swappable)│ │
│  └───────────────────────────────────────────────────────┘  │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
    ┌──────▼──────┐             ┌───────▼────────┐
    │ PostgreSQL  │             │ Filesystem      │
    │ (metadata)  │             │ (dataset bytes, │
    │             │             │  Parquet cache)  │
    └─────────────┘             └────────────────┘
```

Full detail, database schema, and API specification: [`docs/architecture.md`](docs/architecture.md), [`docs/api.md`](docs/api.md).

## AI architecture — the anti-hallucination contract

```
User question
   │
   ▼
LLM decides which tool to call (never computes anything itself)
   │
   ▼
Tool executes against the real Parquet-cached dataframe
   │
   ▼
Result (real numbers) fed back to the LLM
   │
   ▼
LLM explains the result — Answer / Evidence / Interpretation / Next step
```

If a question can't be answered from the tools available, the agent is instructed to say so plainly ("The uploaded dataset does not contain enough information to answer this question") rather than guess. If a tool call fails (bad column name, unsuitable data), the error is fed back to the model so it can retry or explain the limitation — the turn never crashes.

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | React 18 · Vite · TypeScript · Tailwind CSS · Plotly.js · TanStack Query · React Router |
| Backend | FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic |
| Data / Analytics | Pandas · NumPy · SciPy · DuckDB (read-only SQL) |
| ML | scikit-learn (classification/regression/clustering/anomaly) · statsmodels (forecasting) |
| AI | Provider-agnostic LLM client (OpenAI-compatible wire format) with tool/function calling |
| Reports | Jinja2 → HTML, Matplotlib (static charts) → WeasyPrint → PDF |
| Storage | PostgreSQL (metadata) + filesystem (dataset bytes, Parquet cache), storage backend is swappable |
| Ops | Docker · docker-compose · GitHub Actions CI |
| Testing | Pytest (272 backend tests, 96% coverage) · Vitest + React Testing Library (33 frontend tests) |

## Screenshots / demo

Run the app locally (`docker compose up --build` or the local dev instructions below) and visit `http://localhost:5173` — the Dashboard, Dataset Detail (Overview/Preview/Quality/Columns/Visualizations/AI Analysis tabs), and AI Analyst pages are the best places to start. A sample generated report is available by running the report-generation flow described in [Example questions and results](#example-questions-and-results).

## Quick start (Docker)

```bash
git clone <this-repo>
cd ai-data-analyst-agent
cp .env.example .env
# Optionally set LLM_API_KEY and LLM_MODEL in .env to enable the AI Analyst.
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/v1
- Interactive API docs (Swagger UI): http://localhost:8000/docs

No data of your own yet? Two ready-to-upload sample datasets are included in [`data/sample/`](data/sample/) — `ecommerce_sales.csv` (222 rows) and `financial_transactions.csv` (200 rows), both synthetic but deliberately messy (missing values, outliers, duplicates, categorical/datetime columns) so profiling, quality scoring, and the AI Analyst all have something real to find. Regenerate them anytime with `python scripts/seed_sample_data.py`.

Database migrations run automatically on backend container startup (`docker/entrypoint.sh` runs `alembic upgrade head` before starting the server).

> **Note on this repo's own development:** the backend Docker image runs Python 3.11 with the pinned dependency versions in `backend/requirements.txt`. Local development in this repo happened primarily on a newer local Python; if you hit a dependency resolution issue when building the image, please open an issue with the `pip install` output.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate      # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt

# Point DATABASE_URL at a local Postgres, or use SQLite for a quick spin:
export DATABASE_URL="sqlite:///./dev.db"   # PowerShell: $env:DATABASE_URL="sqlite:///./dev.db"
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

By default the frontend expects the API at `http://localhost:8000/api/v1` — override with `VITE_API_BASE_URL` in `frontend/.env.local` if your backend runs elsewhere.

## Environment configuration

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (or a SQLite URL for local dev) |
| `STORAGE_ROOT` | Filesystem root for uploaded files and the Parquet cache |
| `MAX_UPLOAD_SIZE` | Upload size limit in bytes (default 200 MB) |
| `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | AI provider config. Leave `LLM_API_KEY`/`LLM_MODEL` blank to run everything except the AI Analyst — the app reports this honestly (a 503 with a clear message) rather than faking a response. |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |

**On `LLM_MODEL`:** set this to the exact model ID your provider account actually supports — don't assume a convenient-looking alias will keep working. Verify against your provider's current model list before deploying.

## Testing

```bash
# Backend — 272 tests, 96% coverage
cd backend
pytest --cov=app --cov-report=term-missing

# Frontend — 33 tests
cd frontend
npm test
npm run lint
```

Coverage highlights:
- Every analytics engine (profiling, query, correlation, outliers, charts, SQL, forecasting, ML) is unit-tested with crafted DataFrames independent of the API/DB.
- Every API router has integration tests via `TestClient`, including error paths (404/422/503).
- One explicit end-to-end test (`tests/test_e2e_happy_path.py`) chains upload → profile → analysis → chart → AI chat → report generation → invalid-input handling through the real HTTP API in a single connected flow.
- The AI agent's orchestration logic (tool-calling loop, session persistence, error recovery) is tested with a scripted LLM test double — this proves the orchestration code, not what a real LLM would say. `tests/test_ai_api.py` separately proves the API refuses to fake a response when no LLM is configured.

## Project structure

```
ai-data-analyst-agent/
├── frontend/           React + TypeScript + Vite SPA
│   └── src/{components,pages,hooks,services,types,lib}/
├── backend/
│   └── app/
│       ├── api/v1/          FastAPI routers
│       ├── agents/          LLM client, tool router, agent loop, tools/
│       ├── analytics/       Pure computation engines (profiling, query, correlation, outliers, charts, sql, forecasting)
│       ├── ml/               scikit-learn training engines + suggestion
│       ├── reports/         Report data gathering, chart rendering, HTML/PDF rendering
│       ├── services/        Orchestration layer between routers and analytics/ml/reports
│       ├── schemas/         Pydantic request/response models
│       ├── db/               SQLAlchemy models
│       └── storage/          Swappable storage backend (local FS today)
│   ├── alembic/              Migrations
│   └── tests/                272 tests
├── docker/                  Dockerfiles, entrypoint, nginx config
├── docs/                    architecture.md, api.md, deployment.md, roadmap.md
└── .github/workflows/       CI
```

## API documentation

- Interactive Swagger UI at `/docs` when the backend is running.
- Written reference: [`docs/api.md`](docs/api.md).

## Example questions and results

Once a dataset is uploaded and an LLM is configured, the AI Analyst can answer things like:

- "What are the top 10 products by revenue?"
- "Which region has the highest sales?"
- "What happened to revenue over time?"
- "Are there any unusual transactions?"
- "What is the average order value?"
- "Show me the relationship between advertising spend and sales."
- "Which variables are strongly correlated?"
- "Forecast revenue for the next 3 months."
- "Give me an executive summary of this dataset."

Every answer follows **Answer / Evidence / Interpretation / Next step**, and the evidence is a real tool result you can inspect via the "N tool calls used" disclosure under each AI response.

## Limitations

- **Feature importance uses each model's native signal** (Gini importance for tree ensembles, |coefficient| for linear models), not SHAP — a deliberate choice to avoid a heavier, more fragile dependency for marginal benefit at this project's scale.
- **Forecasting covers naive/moving-average/linear/exponential-smoothing**, not ARIMA — automatic order-selection needs extra tooling and can silently produce a worse forecast than an honest simple baseline.
- **PDF report generation needs WeasyPrint's system libraries** (Pango/Cairo/GDK-Pixbuf), provisioned in the Docker image but often missing on a bare Windows dev machine — the API returns a clear `503 pdf_unavailable` rather than crashing; HTML/JSON export are unaffected.
- **No authentication** — this is a single-user local/demo app. See Future improvements.
- **Dataset size**: designed and tested for up to roughly 1M rows / 200MB, held fully in memory via Pandas. Larger datasets would need chunked/streaming processing.
- **SQL tool safety is a keyword blocklist**, not a full SQL parser — a column literally named e.g. `delete` would also be rejected as a defensible trade-off for a small, auditable safety surface.

## Future improvements

- User authentication and per-user dataset isolation.
- Persisted, loadable trained ML models (currently metrics/results are stored; the fitted model object itself is not serialized for later inference).
- Background job queue for large-dataset processing instead of synchronous requests.
- SHAP-based explainability as an opt-in alongside native feature importance.
- Object storage backend (S3-compatible) alongside the existing local filesystem backend.

## License

MIT — see [`LICENSE`](LICENSE).
