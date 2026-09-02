"""Filesystem-backed Storage implementation."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from app.storage.base import Storage, StorageError


class LocalStorage(Storage):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Prevent traversal outside root.
        key = key.lstrip("/\\")
        p = (self.root / key).resolve()
        try:
            p.relative_to(self.root)
        except ValueError as e:
            raise StorageError(f"Invalid storage key: {key!r}") from e
        return p

    def put(self, key: str, fileobj: BinaryIO) -> int:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as out:
            written = 0
            while chunk := fileobj.read(1024 * 1024):
                out.write(chunk)
                written += len(chunk)
        return written

    def get(self, key: str) -> BinaryIO:
        path = self._resolve(key)
        if not path.exists():
            raise StorageError(f"Missing key: {key!r}")
        return path.open("rb")

    def open_path(self, key: str) -> str:
        return str(self._resolve(key))

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    def health(self) -> dict[str, str | bool]:
        writable = False
        try:
            probe = self.root / ".healthcheck"
            probe.write_bytes(b"ok")
            probe.unlink(missing_ok=True)
            writable = True
        except OSError:
            writable = False
        return {"backend": "local", "root": str(self.root), "writable": writable}
