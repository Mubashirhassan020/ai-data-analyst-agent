from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.db.session import engine
from app.storage.factory import get_storage

router = APIRouter(tags=["health"])


class ComponentStatus(BaseModel):
    ok: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    llm_configured: bool
    db: ComponentStatus
    storage: dict


def _check_db() -> ComponentStatus:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return ComponentStatus(ok=True)
    except Exception as e:
        return ComponentStatus(ok=False, detail=type(e).__name__)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    db = _check_db()
    storage_info = get_storage().health()
    overall = "ok" if db.ok and storage_info.get("writable") else "degraded"
    return HealthResponse(
        status=overall,
        version=__version__,
        environment=s.environment,
        llm_configured=s.llm_configured,
        db=db,
        storage=storage_info,
    )
