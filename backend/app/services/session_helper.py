"""Shared helper: get-or-create an AnalysisSession. Used by both the table
query service (/analysis/execute) and the chart service (/analysis/chart) so
saved analyses and saved charts can share one session's timeline."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import models


def get_or_create_analysis_session(
    db: Session, dataset_id: str, session_id: str | None, title: str | None
) -> models.AnalysisSession:
    if session_id:
        session = db.get(models.AnalysisSession, session_id)
        if session is None or session.dataset_id != dataset_id:
            raise NotFoundError(f"Analysis session {session_id} not found for dataset {dataset_id}.")
        return session
    session = models.AnalysisSession(dataset_id=dataset_id, title=title)
    db.add(session)
    db.flush()
    return session
