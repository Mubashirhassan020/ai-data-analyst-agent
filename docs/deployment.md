# Deployment

## Development: Docker Compose

```bash
cp .env.example .env
# edit .env — at minimum, set LLM_API_KEY and LLM_MODEL to enable the AI Analyst
docker compose up --build
```

This starts three services:

| Service | What it does | Port |
|---|---|---|
| `postgres` | Metadata database, persisted in the `pgdata` named volume | 5432 |
| `backend` | FastAPI app. Entrypoint runs `alembic upgrade head` before starting `uvicorn`. | 8000 |
| `frontend` | Vite build served by nginx | 5173 → container port 80 |

The backend won't report healthy until Postgres is healthy (`depends_on: condition: service_healthy`), and the frontend waits on the backend the same way — `docker compose up` brings everything up in the right order on its own.

Uploaded files and the Parquet cache are bind-mounted from `./data` on the host, so they survive a `docker compose down` (but not a `docker compose down -v`, which also drops the Postgres volume).

> **This repository's Docker configuration has not been build-verified in this environment** (no Docker daemon was available while building it). The Dockerfiles, entrypoint, and compose file were hardened through careful manual review — including fixing a real gap where migrations never ran automatically, and correcting the WeasyPrint system-library list — but you should run `docker compose up --build` yourself as the first validation step. The GitHub Actions CI workflow (`.github/workflows/ci.yml`) also builds both images on every push, which is the first automated check of this configuration.

## Production deployment

This app has no single required platform — pick per-component:

- **Frontend**: any static host that serves an SPA with a fallback to `index.html` (Vercel, Netlify, Cloudflare Pages, or the provided nginx container behind any container platform). Set `VITE_API_BASE_URL` at build time to your backend's public URL.
- **Backend**: any container platform that can run the image from `docker/backend.Dockerfile` (Fly.io, Render, Railway, ECS/Fargate, Cloud Run, a bare VM with Docker). Set the environment variables from `.env.example` — at minimum `DATABASE_URL`, `CORS_ORIGINS` (pointed at your deployed frontend origin), `STORAGE_ROOT` (with a persistent volume mounted there), and the `LLM_*` variables.
- **Database**: any managed PostgreSQL 14+ (RDS, Cloud SQL, Supabase, Neon, Railway Postgres, ...). Point `DATABASE_URL` at it; migrations run automatically on backend startup.
- **Storage**: the local filesystem backend needs a persistent volume in production (container filesystems are usually ephemeral). For genuinely durable/scalable storage, implement a new backend against `app/storage/base.py`'s `Storage` protocol (e.g. S3) and set `STORAGE_BACKEND` accordingly — this is a documented future improvement, not yet built.

### Environment variables that matter most in production

| Variable | Production guidance |
|---|---|
| `ENVIRONMENT` | Set to `production` — switches structured logging to JSON output. |
| `CORS_ORIGINS` | Must exactly match your deployed frontend's origin(s), comma-separated. A mismatch here is the most common "the frontend loads but nothing works" cause. |
| `DATABASE_URL` | Use your managed Postgres connection string. Include `?sslmode=require` if your provider requires TLS. |
| `LLM_API_KEY` / `LLM_MODEL` | Required for the AI Analyst. Leaving them blank is valid — the rest of the app works — but the AI endpoints return a clear `503` instead. |
| `MAX_UPLOAD_SIZE` | Tune to your infrastructure's request-body limits (a reverse proxy or load balancer may impose its own cap below this value). |

## Troubleshooting

**"PDF generation is unavailable" (`pdf_unavailable`)**
WeasyPrint needs Pango/Cairo/GDK-Pixbuf (via GObject) system libraries. This is a well-known failure mode on a bare Windows install — the Docker image installs them via apt (`docker/backend.Dockerfile`), so this should only appear if you're running the backend outside Docker on Windows/macOS without the GTK3 runtime. Workaround: use `format: "html"` or `format: "json"` instead, or install WeasyPrint's dependencies per [their install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

**AI Analyst returns 503 `llm_not_configured`**
Set `LLM_API_KEY` and `LLM_MODEL` in `.env` (or your deployment's environment variables) and restart the backend. Verify the model ID is one your provider account actually supports — don't assume a friendly alias name is stable.

**Dataset upload succeeds but every other dataset endpoint 404s / DB errors on startup**
Migrations didn't run. In Docker this shouldn't happen (the entrypoint runs them automatically); if running the backend manually, run `alembic upgrade head` before starting `uvicorn`.

**"no such table" errors when running ad-hoc scripts against the DB**
If you write a one-off script that imports `app.db.base.Base` and calls `Base.metadata.create_all(engine)` without also importing `app.db.models`, SQLAlchemy has nothing registered on `Base.metadata` and creates zero tables. Either `import app.db.models` explicitly, or (preferred) run the real Alembic migrations instead of ad-hoc `create_all()`.

**`pip install` fails to build `pydantic-core` (or another compiled dependency) locally**
This usually means your local Python is newer than the pinned dependency versions have wheels for. Either use Python 3.11 (matching the Docker image) or install with `--only-binary=:all:` and let pip resolve to newer compatible versions — then update `requirements.txt` to match what you actually tested, so Docker doesn't silently diverge from your local environment.

**CORS errors in the browser console**
`CORS_ORIGINS` in the backend's environment must list the exact origin the frontend is served from (scheme + host + port). `http://localhost:5173` and `http://127.0.0.1:5173` are different origins to a browser.

**Frontend builds a huge JS bundle warning**
Plotly.js is lazy-loaded (`React.lazy`) specifically so it doesn't block the initial app bundle — the warning about `PlotlyChartImpl-*.js` being large is expected and only loads when a chart actually renders. The main app bundle itself is ~160KB gzipped.
