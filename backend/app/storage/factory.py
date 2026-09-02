from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import Storage
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    if s.storage_backend == "local":
        return LocalStorage(s.storage_root)
    raise ValueError(f"Unknown storage backend: {s.storage_backend!r}")
