from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    dataset_id: str
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)


class AnalyzeRequest(BaseModel):
    dataset_id: str
    session_id: str | None = None


class ToolCallTrace(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class ChatMessageOut(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessageOut
    tool_calls: list[ToolCallTrace]
    charts: list[dict[str, Any]]


class StoredChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    tool_name: str | None
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    created_at: datetime
