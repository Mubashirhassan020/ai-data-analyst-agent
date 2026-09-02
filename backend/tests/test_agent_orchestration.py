"""Tests the agent's tool-calling loop with a scripted LLM test double — this
verifies MY orchestration code (execute tools, feed results back, persist
messages, stop conditions), not what a real LLM would say. No network calls,
no API key needed. Production always uses the real OpenAICompatibleClient;
see test_ai_api.py for proof the API refuses to fake a response when
unconfigured."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.agent import AgentService
from app.agents.llm_client import LLMResponse, ToolCall
from app.db.session import session_factory
from app.main import app
from app.storage.factory import get_storage

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_sample() -> str:
    client = TestClient(app)
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    r = client.post("/api/v1/datasets/upload", files={"file": ("sample_sales.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


class ScriptedLLMClient:
    """Returns pre-scripted responses in order, one per `.complete()` call."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[list[dict]] = []

    def complete(self, messages, tools=None):
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("ScriptedLLMClient ran out of scripted responses")
        return self._responses.pop(0)


def _service(fake: ScriptedLLMClient) -> AgentService:
    return AgentService(session_factory(), get_storage(), llm_client=fake)


def test_agent_executes_tool_then_answers() -> None:
    ds_id = _upload_sample()
    fake = ScriptedLLMClient([
        LLMResponse(content=None, tool_calls=[ToolCall(id="call_1", name="dataset_schema", arguments={})]),
        LLMResponse(content="**Answer:** The dataset has 10 rows and 6 columns."),
    ])
    result = _service(fake).chat(dataset_id=ds_id, session_id=None, user_message="How big is this dataset?")

    assert result["message"]["content"].startswith("**Answer:**")
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "dataset_schema"
    assert result["tool_calls"][0]["result"]["row_count"] == 10


def test_agent_persists_session_and_messages() -> None:
    ds_id = _upload_sample()
    fake = ScriptedLLMClient([LLMResponse(content="Sure, here's the answer.")])
    result = _service(fake).chat(dataset_id=ds_id, session_id=None, user_message="hello")

    messages = _service(fake).get_messages(result["session_id"])
    assert [m.role for m in messages] == ["user", "assistant"]


def test_agent_reuses_session_and_keeps_history() -> None:
    ds_id = _upload_sample()
    fake = ScriptedLLMClient([
        LLMResponse(content="First answer."),
        LLMResponse(content="Second answer."),
    ])
    service = _service(fake)
    r1 = service.chat(dataset_id=ds_id, session_id=None, user_message="first question")
    r2 = service.chat(dataset_id=ds_id, session_id=r1["session_id"], user_message="follow-up question")

    assert r1["session_id"] == r2["session_id"]
    second_call_contents = [m.get("content") for m in fake.calls[1]]
    assert "first question" in second_call_contents
    assert "First answer." in second_call_contents


def test_agent_reject_session_for_wrong_dataset() -> None:
    import pytest

    from app.core.errors import NotFoundError

    ds_a = _upload_sample()
    ds_b = _upload_sample()
    fake = ScriptedLLMClient([LLMResponse(content="answer")])
    service = _service(fake)
    r1 = service.chat(dataset_id=ds_a, session_id=None, user_message="hi")

    fake2 = ScriptedLLMClient([LLMResponse(content="answer2")])
    with pytest.raises(NotFoundError):
        _service(fake2).chat(dataset_id=ds_b, session_id=r1["session_id"], user_message="hi again")


def test_agent_tool_error_is_fed_back_not_crashed() -> None:
    ds_id = _upload_sample()
    fake = ScriptedLLMClient([
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="call_1", name="run_query", arguments={"group_by": ["not_a_real_column"]})],
        ),
        LLMResponse(content="The uploaded dataset does not contain enough information to answer this question."),
    ])
    result = _service(fake).chat(dataset_id=ds_id, session_id=None, user_message="group by not_a_real_column")

    assert "error" in result["tool_calls"][0]["result"]
    assert "does not contain enough information" in result["message"]["content"]


def test_agent_unknown_tool_name_handled_gracefully() -> None:
    ds_id = _upload_sample()
    fake = ScriptedLLMClient([
        LLMResponse(content=None, tool_calls=[ToolCall(id="call_1", name="not_a_real_tool", arguments={})]),
        LLMResponse(content="I don't have a tool for that."),
    ])
    result = _service(fake).chat(dataset_id=ds_id, session_id=None, user_message="do something unsupported")
    assert "error" in result["tool_calls"][0]["result"]


def test_agent_chart_tool_surfaces_chart_separately() -> None:
    ds_id = _upload_sample()
    fake = ScriptedLLMClient([
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                id="call_1", name="build_chart",
                arguments={"chart_type": "bar", "x": "region", "y": "revenue", "aggregation": "sum"},
            )],
        ),
        LLMResponse(content="Here's the chart."),
    ])
    result = _service(fake).chat(dataset_id=ds_id, session_id=None, user_message="show me revenue by region")
    assert len(result["charts"]) == 1
    assert result["charts"][0]["chart_type"] == "bar"


def test_agent_max_iterations_fallback() -> None:
    ds_id = _upload_sample()
    responses = [
        LLMResponse(content=None, tool_calls=[ToolCall(id=f"call_{i}", name="dataset_schema", arguments={})])
        for i in range(10)
    ]
    fake = ScriptedLLMClient(responses)
    result = _service(fake).chat(dataset_id=ds_id, session_id=None, user_message="loop forever")
    assert "couldn't reach a final answer" in result["message"]["content"]


def test_agent_missing_dataset_raises_not_found() -> None:
    import pytest

    from app.core.errors import NotFoundError

    fake = ScriptedLLMClient([])
    with pytest.raises(NotFoundError):
        _service(fake).chat(dataset_id="does-not-exist", session_id=None, user_message="hi")
