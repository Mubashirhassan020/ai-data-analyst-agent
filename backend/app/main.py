"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIdMiddleware


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    log = get_logger(__name__)

    app = FastAPI(
        title="AI Data Analyst Agent",
        version=__version__,
        description=(
            "Upload a dataset, profile it, visualize it, and chat with a tool-using "
            "AI analyst that answers with real computations."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Order matters: RequestId first so CORS responses also carry the header
    # (CORSMiddleware handles OPTIONS itself and short-circuits later middleware).
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.include_router(api_router)

    log.info("app_started", environment=settings.environment, version=__version__)
    return app


app = create_app()
