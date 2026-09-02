"""Orchestrates dataset profiling: load data, compute the profile, persist it."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.profiling import compute_profile
from app.core.logging import get_logger
from app.db import models
from app.services.dataset_service import DatasetService
from app.storage.base import Storage

log = get_logger(__name__)


class ProfilingService:
    def __init__(self, db: Session, storage: Storage) -> None:
        self.db = db
        self.dataset_service = DatasetService(db, storage)

    def get_or_compute(self, dataset_id: str, *, refresh: bool = False) -> dict:
        ds = self.dataset_service.get(dataset_id)

        existing = (
            self.db.query(models.DatasetProfile)
            .filter(models.DatasetProfile.dataset_id == dataset_id)
            .one_or_none()
        )
        if existing is not None and not refresh:
            payload = dict(existing.summary)
            payload["dataset_id"] = dataset_id
            payload["cached"] = True
            return payload

        df = self.dataset_service.load_dataframe(dataset_id)
        result = compute_profile(df)

        self._persist(ds, result, existing)

        payload = dict(result)
        payload["dataset_id"] = dataset_id
        payload["cached"] = False
        return payload

    def _persist(
        self,
        ds: models.Dataset,
        result: dict,
        existing: models.DatasetProfile | None,
    ) -> None:
        now = datetime.now(UTC)
        if existing is None:
            existing = models.DatasetProfile(dataset_id=ds.id)
            self.db.add(existing)
        existing.summary = result
        existing.quality_score = result["quality"]["overall"]
        existing.issues = result["issues"]
        existing.generated_at = now

        by_name = {c.name: c for c in ds.columns}
        for col in result["columns"]:
            row = by_name.get(col["name"])
            if row is None:
                continue
            row.inferred_type = col["inferred_type"]
            row.logical_type = col["logical_type"]
            row.null_count = col["null_count"]
            row.unique_count = col["unique_count"]
            row.min_value = col["min_value"]
            row.max_value = col["max_value"]
            row.stats = {
                "numeric": col["numeric"],
                "categorical": col["categorical"],
                "datetime": col["datetime"],
                "boolean": col["boolean"],
            }

        self.db.commit()
        log.info(
            "dataset_profiled",
            dataset_id=ds.id,
            quality_score=result["quality"]["overall"],
            issue_count=len(result["issues"]),
        )
