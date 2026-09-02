from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ReportFormat = Literal["html", "pdf", "json"]


class ReportGenerateRequest(BaseModel):
    dataset_id: str
    format: ReportFormat = "html"


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    format: str
    sections: list[str]
    created_at: datetime
