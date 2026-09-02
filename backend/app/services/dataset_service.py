"""Dataset ingestion: validate, persist original bytes, normalize to Parquet, record metadata.

The Parquet cache is what every downstream service reads. The original file is retained
for provenance and for the "download original" future feature.
"""
from __future__ import annotations

import io
from pathlib import PurePosixPath
from typing import BinaryIO

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, UnsupportedFileError, ValidationError
from app.core.logging import get_logger
from app.db import models
from app.storage.base import Storage

log = get_logger(__name__)

_CSV_EXTS = {"csv", "tsv", "txt"}
_EXCEL_EXTS = {"xlsx", "xls"}


def _ext_of(name: str) -> str:
    return PurePosixPath(name).suffix.lstrip(".").lower()


def _detect_delimiter(sample: bytes) -> str:
    """Small heuristic used only when the extension is generic (csv/tsv/txt)."""
    head = sample[:8192].decode("utf-8", errors="ignore")
    counts = {c: head.count(c) for c in (",", "\t", ";", "|")}
    return max(counts, key=counts.get) if any(counts.values()) else ","


def _read_dataframe(raw: bytes, ext: str) -> pd.DataFrame:
    if ext in _EXCEL_EXTS:
        try:
            return pd.read_excel(io.BytesIO(raw))
        except Exception as e:
            raise ValidationError(f"Could not read Excel file: {e}") from e
    if ext in _CSV_EXTS:
        sep = "\t" if ext == "tsv" else _detect_delimiter(raw)
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(raw), sep=sep, encoding=enc)
            except UnicodeDecodeError:
                continue
            except pd.errors.EmptyDataError as e:
                raise ValidationError("Uploaded file is empty.") from e
            except Exception as e:
                raise ValidationError(f"Could not parse CSV: {e}") from e
        raise ValidationError("Could not decode file with common encodings.")
    raise UnsupportedFileError(f"Unsupported file extension: .{ext}")


def _infer_type(series: pd.Series) -> str:
    """Coarse type used at upload time. Full profiling arrives in Phase 4."""
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    non_null = series.dropna()
    if not non_null.empty and non_null.nunique() / max(len(non_null), 1) < 0.5:
        return "categorical"
    return "text"


class DatasetService:
    def __init__(self, db: Session, storage: Storage) -> None:
        self.db = db
        self.storage = storage
        self.settings = get_settings()

    # ---------- validation ----------

    def _validate_upload(self, filename: str, size: int) -> str:
        if not filename:
            raise ValidationError("Missing filename.")
        ext = _ext_of(filename)
        allowed = self.settings.allowed_extension_set
        if ext not in allowed:
            raise UnsupportedFileError(
                f"Extension .{ext or '(none)'} is not allowed.",
                details={"allowed": sorted(allowed)},
            )
        if size <= 0:
            raise ValidationError("Uploaded file is empty.")
        if size > self.settings.max_upload_size:
            raise ValidationError(
                f"File exceeds max upload size of {self.settings.max_upload_size} bytes.",
                details={"file_size": size, "limit": self.settings.max_upload_size},
            )
        return ext

    # ---------- ingest ----------

    def ingest(
        self,
        *,
        filename: str,
        fileobj: BinaryIO,
        size: int,
        mime_type: str | None,
    ) -> models.Dataset:
        ext = self._validate_upload(filename, size)
        raw = fileobj.read()
        if len(raw) != size:
            # streamed read differed from Content-Length; use the actual length
            size = len(raw)

        # Persist original bytes first so we always have provenance.
        ds = models.Dataset(
            original_filename=filename,
            storage_key="",  # temp, updated after storage write
            file_size_bytes=size,
            mime_type=mime_type,
            status="processing",
        )
        self.db.add(ds)
        self.db.flush()  # populate ds.id

        original_key = f"uploads/{ds.id}/{filename}"
        parquet_key = f"processed/{ds.id}.parquet"
        ds.storage_key = original_key
        self.storage.put(original_key, io.BytesIO(raw))

        try:
            df = _read_dataframe(raw, ext)
        except (ValidationError, UnsupportedFileError) as e:
            ds.status = "failed"
            ds.error_message = e.message
            self.db.commit()
            raise

        if df.shape[1] == 0:
            ds.status = "failed"
            ds.error_message = "No columns detected."
            self.db.commit()
            raise ValidationError("No columns detected in file.")

        # Normalize column names (str) and persist parquet cache.
        df.columns = [str(c) for c in df.columns]
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        buf.seek(0)
        self.storage.put(parquet_key, buf)

        ds.parquet_key = parquet_key
        ds.row_count = int(df.shape[0])
        ds.column_count = int(df.shape[1])
        ds.status = "ready"

        # Record column stubs (full profiling lands in Phase 4).
        for pos, name in enumerate(df.columns):
            col = df[name]
            self.db.add(
                models.DatasetColumn(
                    dataset_id=ds.id,
                    name=name,
                    position=pos,
                    inferred_type=_infer_type(col),
                    null_count=int(col.isna().sum()),
                    unique_count=int(col.nunique(dropna=True)),
                )
            )

        self.db.commit()
        self.db.refresh(ds)
        log.info(
            "dataset_ingested",
            dataset_id=ds.id,
            rows=ds.row_count,
            cols=ds.column_count,
            bytes=size,
        )
        return ds

    # ---------- read ----------

    def list(self) -> list[models.Dataset]:
        return (
            self.db.query(models.Dataset).order_by(models.Dataset.created_at.desc()).all()
        )

    def get(self, dataset_id: str) -> models.Dataset:
        ds = self.db.get(models.Dataset, dataset_id)
        if ds is None:
            raise NotFoundError(f"Dataset {dataset_id} not found.")
        return ds

    def delete(self, dataset_id: str) -> None:
        ds = self.get(dataset_id)
        for key in (ds.storage_key, ds.parquet_key):
            if key and self.storage.exists(key):
                self.storage.delete(key)
        self.db.delete(ds)
        self.db.commit()

    # ---------- preview ----------

    def load_dataframe(self, dataset_id: str) -> pd.DataFrame:
        ds = self.get(dataset_id)
        if not ds.parquet_key or ds.status != "ready":
            raise ValidationError(f"Dataset {dataset_id} is not ready (status={ds.status}).")
        with self.storage.get(ds.parquet_key) as f:
            return pd.read_parquet(f)

    def preview(
        self,
        dataset_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        sort: str | None = None,
        sort_dir: str = "asc",
        search: str | None = None,
    ) -> dict:
        df = self.load_dataframe(dataset_id)

        if search:
            mask = df.astype(str).apply(
                lambda col: col.str.contains(search, case=False, na=False, regex=False)
            ).any(axis=1)
            df = df[mask]

        if sort and sort in df.columns:
            df = df.sort_values(by=sort, ascending=(sort_dir != "desc"), kind="mergesort")

        total_rows = int(df.shape[0])
        page_size = max(1, min(page_size, 500))
        page = max(1, page)
        total_pages = max(1, (total_rows + page_size - 1) // page_size)
        start = (page - 1) * page_size
        page_df = df.iloc[start : start + page_size]

        rows = page_df.astype(object).where(pd.notnull(page_df), None).to_dict(orient="records")
        return {
            "columns": [str(c) for c in df.columns],
            "rows": rows,
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages,
        }
