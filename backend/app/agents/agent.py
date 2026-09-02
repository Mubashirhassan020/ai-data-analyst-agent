"""The agent orchestration loop: LLM decides which tool to call, this code
executes it against the real dataset, the LLM explains the result. The model
never receives dataset facts except through tool results — see prompts.py.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.agents.llm_client import LLMClient, get_llm_client
from app.agents.prompts import build_system_prompt
from app.agents.tools import ALL_TOOLS, ToolContext, get_tool_specs
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.core.logging import get_logger
from app.db import models
from app.services.dataset_service import DatasetService
from app.storage.base import Storage

log = get_logger(__name__)

# Tool results (chart traces, query rows) can contain large arrays; the LLM only
# needs enough to explain the result, not the full payload — the frontend gets
# the untrimmed result via `tool_calls`/`charts` in the response regardless.
MAX_ARRAY_ITEMS_FOR_LLM = 20


def _trim_for_llm(value: Any) -> Any:
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_ITEMS_FOR_LLM:
            head = [_trim_for_llm(v) for v in value[:MAX_ARRAY_ITEMS_FOR_LLM]]
            return head + [f"...{len(value) - MAX_ARRAY_ITEMS_FOR_LLM} more items truncated"]
        return [_trim_for_llm(v) for v in value]
    if isinstance(value, dict):
        return {k: _trim_for_llm(v) for k, v in value.items()}
    return value


class AgentService:
    def __init__(self, db: Session, storage: Storage, llm_client: LLMClient | None = None) -> None:
        self.db = db
        self.storage = storage
        self.dataset_service = DatasetService(db, storage)
        self._llm_client = llm_client

    def _get_llm(self) -> LLMClient:
        # Lazy + raises LLMNotConfiguredError here (not in __init__) so a service
        # instance can be constructed freely; the 503 only fires when actually needed.
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def chat(self, *, dataset_id: str, session_id: str | None, user_message: str) -> dict[str, Any]:
        ds = self.dataset_service.get(dataset_id)
        llm = self._get_llm()  # fail fast, before creating any session/message rows

        session = self._get_or_create_session(dataset_id, session_id)
        self._save_message(session.id, role="user", content=user_message)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(ds.row_count, ds.column_count)},
            *self._load_history(session.id),
        ]

        tool_specs = get_tool_specs()
        ctx = ToolContext(db=self.db, storage=self.storage, dataset_id=dataset_id)
        tool_trace: list[dict[str, Any]] = []
        charts: list[dict[str, Any]] = []
        settings = get_settings()

        for _ in range(settings.llm_max_tool_iterations):
            response = llm.complete(messages, tools=tool_specs)

            if not response.tool_calls:
                final_text = response.content or "I wasn't able to generate a response."
                self._save_message(session.id, role="assistant", content=final_text)
                return {
                    "session_id": session.id,
                    "message": {"role": "assistant", "content": final_text},
                    "tool_calls": tool_trace,
                    "charts": charts,
                }

            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in response.tool_calls
                ],
            })

            for tc in response.tool_calls:
                result = self._execute_tool(tc.name, tc.arguments, ctx)
                if tc.name == "build_chart" and "error" not in result:
                    charts.append(result)
                tool_trace.append({"name": tc.name, "arguments": tc.arguments, "result": result})
                self._save_message(
                    session.id, role="tool", content="",
                    tool_name=tc.name, tool_args=tc.arguments, tool_result=result,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(_trim_for_llm(result)),
                })

        fallback = "I made several tool calls but couldn't reach a final answer. Please try rephrasing your question."
        self._save_message(session.id, role="assistant", content=fallback)
        return {
            "session_id": session.id,
            "message": {"role": "assistant", "content": fallback},
            "tool_calls": tool_trace,
            "charts": charts,
        }

    def get_messages(self, session_id: str) -> list[models.ChatMessage]:
        session = self.db.get(models.ChatSession, session_id)
        if session is None:
            raise NotFoundError(f"Chat session {session_id} not found.")
        return session.messages

    def _execute_tool(self, name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        tool = ALL_TOOLS.get(name)
        if tool is None:
            return {"error": f"Unknown tool: {name!r}"}
        try:
            return tool.execute(args, ctx)
        except AppError as e:
            return {"error": e.message}
        except Exception as e:  # noqa: BLE001 - tool failures must surface to the LLM, never crash the turn
            log.exception("tool_execution_failed", tool=name)
            return {"error": f"Tool execution failed: {e}"}

    def _get_or_create_session(self, dataset_id: str, session_id: str | None) -> models.ChatSession:
        if session_id:
            session = self.db.get(models.ChatSession, session_id)
            if session is None or session.dataset_id != dataset_id:
                raise NotFoundError(f"Chat session {session_id} not found for dataset {dataset_id}.")
            return session
        session = models.ChatSession(dataset_id=dataset_id)
        self.db.add(session)
        self.db.flush()
        return session

    def _load_history(self, session_id: str) -> list[dict[str, Any]]:
        """Reconstruct prior turns as plain user/assistant text. Tool-call messages
        are intentionally not replayed — the assistant's final synthesized answer
        already carries what was found, and OpenAI's API requires any replayed
        `tool` message to be paired with a matching `tool_calls` message, which
        would add complexity with no benefit to the model's ability to answer
        follow-up questions."""
        session = self.db.get(models.ChatSession, session_id)
        return [
            {"role": m.role, "content": m.content}
            for m in session.messages
            if m.role in ("user", "assistant")
        ]

    def _save_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
    ) -> None:
        msg = models.ChatMessage(
            session_id=session_id, role=role, content=content,
            tool_name=tool_name, tool_args=tool_args, tool_result=tool_result,
        )
        self.db.add(msg)
        self.db.commit()
