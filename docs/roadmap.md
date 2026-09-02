# Implementation Roadmap

Each phase ends in a runnable, testable state.

| # | Phase | Scope | Status |
|---|---|---|---|
| 1 | Scaffolding | Repo, docker-compose, FastAPI + React skeleton, health endpoint | ✅ done |
| 2 | Backend foundation | DB, Alembic, storage abstraction, request-id middleware | ✅ done |
| 3 | Dataset upload | Validation, Parquet normalization, CRUD | ✅ done |
| 4 | Data profiling | Types, stats, quality score, preview, column detail | ✅ done |
| 5 | Analytics engine | Deterministic Pandas ops, aggregations, filters | ✅ done |
| 6 | Visualization | Plotly spec generator | ✅ done |
| 7 | Frontend | Landing, dashboard, dataset detail, viz builder | ✅ done |
| 8 | AI agent core | LLM client, tool router, sessions | ✅ done |
| 9 | AI tools | schema, summary, pandas, sql (DuckDB), viz, corr, outlier, forecast | ✅ done |
| 10 | ML | suggest, train, evaluate, feature importance | ✅ done |
| 11 | Reports | HTML + PDF | ✅ done |
| 12 | Test hardening | unit + integration | ✅ done |
| 13 | Docker polish | multi-stage, healthchecks, volumes, migrations-on-boot | ✅ done |
| 14 | CI | GitHub Actions | ✅ done |
| 15 | Docs | README, architecture, api, deployment | ✅ done |

All 15 phases complete. See the [README](../README.md) for the full feature list and quick start.

## Anti-hallucination contract

The LLM is never asked for facts. It decides *which* tool to call and *how* to
explain the result. All numeric answers round-trip through Pandas/SQL/ML. If no
tool can answer, the agent must respond with "insufficient data."
