"""Provider-agnostic LLM client for tool-calling chat completions.

Only one adapter ships today (OpenAI-compatible: works against OpenAI itself and
any gateway/proxy — Azure OpenAI, LiteLLM, local vLLM/Ollama — that exposes the
same `/chat/completions` + `tools` contract). Swapping providers means adding a
new class that satisfies `LLMClient`, not touching the agent loop.

This module never fabricates a response: if no API key/model is configured, the
factory raises `LLMNotConfiguredError` rather than returning a fake completion.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError, LLMNotConfiguredError
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


class LLMCallError(AppError):
    status_code = 502
    code = "llm_call_failed"


class LLMClient(Protocol):
    def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse: ...


class OpenAICompatibleClient:
    """Talks to any `/v1/chat/completions` endpoint using the OpenAI tool-calling
    wire format (`tools` + `tool_calls` in the response message)."""

    def __init__(self, settings: Settings) -> None:
        if not settings.llm_configured:
            raise LLMNotConfiguredError(
                "LLM is not configured. Set LLM_API_KEY and LLM_MODEL to enable AI features."
            )
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_seconds

    def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        payload: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.error("llm_http_error", status=e.response.status_code, body=e.response.text[:500])
            raise LLMCallError(f"LLM provider returned {e.response.status_code}.") from e
        except httpx.HTTPError as e:
            log.error("llm_request_error", error=str(e))
            raise LLMCallError("Could not reach the LLM provider.") from e

        body = resp.json()
        choice = body["choices"][0]
        msg = choice["message"]

        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(id=tc["id"], name=tc["function"]["name"], arguments=args))

        return LLMResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
        )


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """Factory used by the agent service. Raises LLMNotConfiguredError if unset —
    callers should let that propagate to a 503, never substitute a fake client."""
    return OpenAICompatibleClient(settings or get_settings())
