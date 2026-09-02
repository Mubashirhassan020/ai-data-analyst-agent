"""FastAPI dependency providers."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.storage.base import Storage
from app.storage.factory import get_storage as _get_storage


def storage_dep() -> Storage:
    return _get_storage()


DbSession = Annotated[Session, Depends(get_session)]
StorageDep = Annotated[Storage, Depends(storage_dep)]
