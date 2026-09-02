from __future__ import annotations

from fastapi import APIRouter, Response

from app.core.deps import DbSession, StorageDep
from app.schemas.report import ReportGenerateRequest, ReportOut
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportOut, status_code=201)
async def generate_report(payload: ReportGenerateRequest, db: DbSession, storage: StorageDep) -> ReportOut:
    service = ReportService(db, storage)
    report = service.generate(payload)
    return ReportOut.model_validate(report)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: str, db: DbSession, storage: StorageDep) -> ReportOut:
    service = ReportService(db, storage)
    report = service.get(report_id)
    return ReportOut.model_validate(report)


@router.get("/{report_id}/download")
async def download_report(report_id: str, db: DbSession, storage: StorageDep) -> Response:
    service = ReportService(db, storage)
    content, content_type, filename = service.get_content(report_id)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
