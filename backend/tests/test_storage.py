import io

import pytest

from app.storage.base import StorageError
from app.storage.local import LocalStorage


def test_local_storage_roundtrip(tmp_path) -> None:
    store = LocalStorage(tmp_path)
    n = store.put("a/b/hello.txt", io.BytesIO(b"hi there"))
    assert n == 8
    assert store.exists("a/b/hello.txt")
    with store.get("a/b/hello.txt") as f:
        assert f.read() == b"hi there"
    store.delete("a/b/hello.txt")
    assert not store.exists("a/b/hello.txt")


def test_local_storage_rejects_traversal(tmp_path) -> None:
    store = LocalStorage(tmp_path)
    with pytest.raises(StorageError):
        store.put("../escape.txt", io.BytesIO(b"nope"))


def test_local_storage_health(tmp_path) -> None:
    h = LocalStorage(tmp_path).health()
    assert h["writable"] is True
    assert h["backend"] == "local"
