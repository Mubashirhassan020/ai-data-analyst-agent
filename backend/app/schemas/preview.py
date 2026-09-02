from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PreviewPage(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    page: int
    page_size: int
    total_rows: int
    total_pages: int
