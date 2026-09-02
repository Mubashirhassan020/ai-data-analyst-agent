"""Tool contract: every tool the agent can call takes a JSON-schema-described set
of arguments and a `ToolContext` (DB + storage, scoped to one dataset), and
returns a plain JSON-serializable dict — always computed from the real dataset,
never invented by the LLM."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd
from sqlalchemy.orm import Session

from app.services.dataset_service import DatasetService
from app.storage.base import Storage


@dataclass
class ToolContext:
    db: Session
    storage: Storage
    dataset_id: str

    _df_cache: pd.DataFrame | None = None

    def dataframe(self) -> pd.DataFrame:
        """Loaded once per tool-call turn and cached — the agent loop may call
        several tools against the same dataset within one user turn."""
        if self._df_cache is None:
            self._df_cache = DatasetService(self.db, self.storage).load_dataframe(self.dataset_id)
        return self._df_cache


class ToolExecutor(Protocol):
    def __call__(self, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]: ...


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the arguments object
    execute: Callable[[dict[str, Any], ToolContext], dict[str, Any]]

    def spec(self) -> dict[str, Any]:
        """OpenAI-compatible function-calling tool spec."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
