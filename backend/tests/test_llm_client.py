"""Unit tests for the LLM client: config validation and OpenAI wire-format
parsing, using a mocked HTTP layer (no real network calls, no API key needed)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.agents.llm_client import LLMCallError, OpenAICompatibleClient, get_llm_client
from app.core.config import Settings
from app.core.errors import LLMNotConfiguredError


def test_get_llm_client_raises_when_unconfigured() -> None:
    settings = Settings(llm_api_key="", llm_model="")
    with pytest.raises(LLMNotConfiguredError):
        get_llm_client(settings)


def test_get_llm_client_succeeds_when_configured() -> None:
    settings = Settings(llm_api_key="test-key", llm_model="test-model")
    client = get_llm_client(settings)
    assert isinstance(client, OpenAICompatibleClient)


def test_parses_tool_calls_from_response() -> None:
    settings = Settings(llm_api_key="test-key", llm_model="test-model", llm_base_url="https://example.invalid/v1")
    client = OpenAICompatibleClient(settings)

    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "choices": [{
            "message": {
                "content": None,
                "tool_calls": [{"id": "call_1", "function": {"name": "dataset_schema", "arguments": "{}"}}],
            },
            "finish_reason": "tool_calls",
        }]
    }
    with patch("app.agents.llm_client.httpx.post", return_value=fake_response) as mock_post:
        result = client.complete(
            [{"role": "user", "content": "hi"}],
            tools=[{"type": "function", "function": {"name": "dataset_schema"}}],
        )

    assert result.tool_calls[0].id == "call_1"
    assert result.tool_calls[0].name == "dataset_schema"
    assert result.tool_calls[0].arguments == {}
    assert result.finish_reason == "tool_calls"
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_parses_final_content_without_tool_calls() -> None:
    settings = Settings(llm_api_key="test-key", llm_model="test-model")
    client = OpenAICompatibleClient(settings)
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}]}
    with patch("app.agents.llm_client.httpx.post", return_value=fake_response):
        result = client.complete([{"role": "user", "content": "hi"}])
    assert result.content == "Hello!"
    assert result.tool_calls == []


def test_parses_tool_call_with_malformed_json_arguments() -> None:
    settings = Settings(llm_api_key="test-key", llm_model="test-model")
    client = OpenAICompatibleClient(settings)
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "choices": [{
            "message": {"content": None, "tool_calls": [{"id": "call_1", "function": {"name": "x", "arguments": "not json"}}]},
            "finish_reason": "tool_calls",
        }]
    }
    with patch("app.agents.llm_client.httpx.post", return_value=fake_response):
        result = client.complete([{"role": "user", "content": "hi"}])
    assert result.tool_calls[0].arguments == {}


def test_raises_llm_call_error_on_connection_failure() -> None:
    settings = Settings(llm_api_key="test-key", llm_model="test-model")
    client = OpenAICompatibleClient(settings)
    with patch("app.agents.llm_client.httpx.post", side_effect=httpx.ConnectError("boom")), pytest.raises(LLMCallError):
        client.complete([{"role": "user", "content": "hi"}])


def test_raises_llm_call_error_on_http_status_error() -> None:
    settings = Settings(llm_api_key="test-key", llm_model="test-model")
    client = OpenAICompatibleClient(settings)
    fake_response = MagicMock()
    fake_response.status_code = 401
    fake_response.text = "unauthorized"
    http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=fake_response)
    fake_response.raise_for_status.side_effect = http_error
    with patch("app.agents.llm_client.httpx.post", return_value=fake_response), pytest.raises(LLMCallError):
        client.complete([{"role": "user", "content": "hi"}])
