"""Pydantic request/response models for datasets."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatasetOut(BaseModel):
    """Public dataset record. `storage_key`/`parquet_key` are internal."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    file_size_bytes: int
    mime_type: str | None
    row_count: int | None
    column_count: int | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    position: int
    inferred_type: str
    null_count: int
    unique_count: int


class DatasetDetail(DatasetOut):
    columns: list[ColumnOut] = Field(default_factory=list)


class ColumnDetail(BaseModel):
    """Full column metadata, including profiling stats once available."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    position: int
    inferred_type: str
    logical_type: str | None
    null_count: int
    unique_count: int
    min_value: str | None
    max_value: str | None
    stats: dict[str, Any] | None
