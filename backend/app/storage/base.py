"""Storage backend protocol. Object-storage-ready abstraction over the filesystem."""
from __future__ import annotations

from typing import BinaryIO, Protocol


class StorageError(Exception):
    """Raised when a storage backend fails an operation."""


class Storage(Protocol):
    """Backend contract. Keys are opaque strings; the backend maps them to a location."""

    def put(self, key: str, fileobj: BinaryIO) -> int:
        """Write bytes; return number of bytes written."""

    def get(self, key: str) -> BinaryIO:
        """Return a readable binary handle. Caller must close."""

    def open_path(self, key: str) -> str:
        """Return an OS path suitable for tools like Pandas / DuckDB (local backends only)."""

    def exists(self, key: str) -> bool:
        ...

    def delete(self, key: str) -> None:
        ...

    def health(self) -> dict[str, str | bool]:
        """Return a small dict describing backend status (for /health)."""
