"""Shared pytest fixtures. Uses SQLite + a temp storage root so tests never touch Postgres."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# Configure app for testing BEFORE app modules import settings.
_TMP = tempfile.mkdtemp(prefix="ai-analyst-test-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(_TMP) / 'test.db'}")
os.environ.setdefault("STORAGE_ROOT", str(Path(_TMP) / "storage"))
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://testserver")

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.storage.factory import get_storage  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_schema() -> Iterator[None]:
    get_settings.cache_clear()
    get_storage.cache_clear()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
