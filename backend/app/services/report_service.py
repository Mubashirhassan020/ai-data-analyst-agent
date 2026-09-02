"""Orchestrates report generation: gather real data, render HTML, optionally
convert to PDF or serialize to JSON, persist to storage, and record a Report row."""
from __future__ import annotations

import io
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db import models
from app.reports.data_builder import build_report_data
from app.reports.renderer import render_html, render_pdf
from app.schemas.report import ReportGenerateRequest
from app.storage.base import Storage

log = get_logger(__name__)

ALL_SECTIONS = [
    "executive_summary", "dataset_overview", "data_quality", "key_statistics",
    "visualizations", "anomalies", "ai_insight", "recommendations", "methodology", "limitations",
]

_CONTENT_TYPES = {"html": "text/html", "pdf": "application/pdf", "json": "application/json"}
_EXTENSIONS = {"html": "html", "pdf": "pdf", "json": "json"}


class ReportService:
    def __init__(self, db: Session, storage: Storage) -> None:
        self.db = db
        self.storage = storage

    def generate(self, req: ReportGenerateRequest) -> models.Report:
        report_data = build_report_data(self.db, self.storage, req.dataset_id)
        content = self._render(req.format, report_data)

        report_row = models.Report(
            dataset_id=req.dataset_id, format=req.format, storage_key="", sections=ALL_SECTIONS
        )
        self.db.add(report_row)
        self.db.flush()

        storage_key = f"reports/{report_row.id}.{_EXTENSIONS[req.format]}"
        self.storage.put(storage_key, io.BytesIO(content))
        report_row.storage_key = storage_key
        self.db.commit()
        self.db.refresh(report_row)

        log.info("report_generated", dataset_id=req.dataset_id, report_id=report_row.id, format=req.format)
        return report_row

    def get(self, report_id: str) -> models.Report:
        report = self.db.get(models.Report, report_id)
        if report is None:
            raise NotFoundError(f"Report {report_id} not found.")
        return report

    def get_content(self, report_id: str) -> tuple[bytes, str, str]:
        report = self.get(report_id)
        with self.storage.get(report.storage_key) as f:
            content = f.read()
        filename = f"report_{report.dataset_id}.{_EXTENSIONS[report.format]}"
        return content, _CONTENT_TYPES[report.format], filename

    @staticmethod
    def _render(fmt: str, report_data: dict[str, Any]) -> bytes:
        if fmt == "html":
            return render_html(report_data).encode("utf-8")
        if fmt == "pdf":
            return render_pdf(render_html(report_data))
        if fmt == "json":
            return json.dumps(report_data, indent=2, default=str).encode("utf-8")
        raise ValidationError(f"Unsupported report format: {fmt!r}")
