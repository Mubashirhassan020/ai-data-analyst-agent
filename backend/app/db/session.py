"""Database engine and session management."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()


def _build_engine() -> Engine:
    return create_engine(
        _settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


engine: Engine = _build_engine()
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a scoped session and closes it."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
