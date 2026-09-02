"""One full happy-path integration test chaining the entire user journey:
upload -> profile -> analysis -> chart -> AI response -> report generation ->
graceful error handling. This is the explicit "Upload -> profile -> analysis
-> AI response" integration test the project spec calls for, run once as a
single connected flow rather than only as isolated per-feature tests.

The AI step uses a scripted LLM test double (see test_agent_orchestration.py
for the rationale) standing in for the network call — this proves the real
HTTP API, agent loop, tool execution, and persistence all work together
end-to-end, without depending on a live LLM provider or API key.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.llm_client import LLMResponse, ToolCall
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


class _ScriptedLLM:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)

    def complete(self, messages, tools=None):  # noqa: ARG002 - matches LLMClient protocol
        return self._responses.pop(0)


def test_full_happy_path_upload_profile_analysis_ai_report() -> None:
    client = TestClient(app)

    # 1. Upload
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    upload_resp = client.post(
        "/api/v1/datasets/upload", files={"file": ("sample_sales.csv", content, "text/csv")}
    )
    assert upload_resp.status_code == 201, upload_resp.text
    dataset = upload_resp.json()
    ds_id = dataset["id"]
    assert dataset["status"] == "ready"
    assert dataset["row_count"] == 10

    # 2. Profile
    profile_resp = client.get(f"/api/v1/datasets/{ds_id}/profile")
    assert profile_resp.status_code == 200, profile_resp.text
    profile = profile_resp.json()
    assert profile["quality"]["overall"] == 90
    assert any(i["type"] == "missing_values" for i in profile["issues"])

    # 3. Columns reflect the profiling type-upgrade from Phase 4
    columns_resp = client.get(f"/api/v1/datasets/{ds_id}/columns")
    assert columns_resp.status_code == 200
    order_date = next(c for c in columns_resp.json() if c["name"] == "order_date")
    assert order_date["inferred_type"] == "datetime"

    # 4. Deterministic analysis: which region has the highest revenue
    analysis_resp = client.post(
        "/api/v1/analysis/execute",
        json={
            "dataset_id": ds_id,
            "group_by": ["region"],
            "metrics": [{"aggregation": "sum", "column": "revenue", "alias": "total"}],
            "sort": {"by": "total", "direction": "desc"},
            "limit": 1,
        },
    )
    assert analysis_resp.status_code == 200, analysis_resp.text
    assert analysis_resp.json()["rows"][0]["region"] == "West"

    # 5. Chart generation
    chart_resp = client.post(
        "/api/v1/analysis/chart",
        json={"dataset_id": ds_id, "chart_type": "bar", "x": "region", "y": "revenue", "aggregation": "sum"},
    )
    assert chart_resp.status_code == 200
    assert chart_resp.json()["data"][0]["type"] == "bar"

    # 6. AI response, grounded in a real tool call
    fake_llm = _ScriptedLLM([
        LLMResponse(content=None, tool_calls=[ToolCall(
            id="call_1", name="run_query",
            arguments={
                "group_by": ["region"],
                "metrics": [{"aggregation": "sum", "column": "revenue", "alias": "total"}],
                "sort": {"by": "total", "direction": "desc"}, "limit": 1,
            },
        )]),
        LLMResponse(content="**Answer:** West generated the most revenue.\n**Evidence:** West total = $361.50."),
    ])
    with patch("app.agents.agent.get_llm_client", return_value=fake_llm):
        chat_resp = client.post(
            "/api/v1/ai/chat", json={"dataset_id": ds_id, "message": "Which region made the most revenue?"}
        )
    assert chat_resp.status_code == 200, chat_resp.text
    chat_body = chat_resp.json()
    assert "West" in chat_body["message"]["content"]
    assert chat_body["tool_calls"][0]["name"] == "run_query"
    # The AI's claim is traceable to an actual tool result, not invented.
    assert chat_body["tool_calls"][0]["result"]["rows"][0]["region"] == "West"
    session_id = chat_body["session_id"]

    # 7. Chat history persisted and retrievable
    messages_resp = client.get(f"/api/v1/ai/sessions/{session_id}/messages")
    assert messages_resp.status_code == 200
    assert [m["role"] for m in messages_resp.json()] == ["user", "tool", "assistant"]

    # 8. Follow-up question in the same session retains conversational context
    fake_llm_2 = _ScriptedLLM([LLMResponse(content="Based on our conversation, West remains the top region.")])
    with patch("app.agents.agent.get_llm_client", return_value=fake_llm_2):
        followup_resp = client.post(
            "/api/v1/ai/chat",
            json={"dataset_id": ds_id, "session_id": session_id, "message": "Are you sure?"},
        )
    assert followup_resp.status_code == 200
    assert followup_resp.json()["session_id"] == session_id

    # 9. Report generation pulls in the real profile and the AI conversation just had
    report_resp = client.post("/api/v1/reports/generate", json={"dataset_id": ds_id, "format": "json"})
    assert report_resp.status_code == 201, report_resp.text
    report = report_resp.json()
    download_resp = client.get(f"/api/v1/reports/{report['id']}/download")
    report_data = download_resp.json()
    assert report_data["dataset"]["row_count"] == 10
    assert report_data["ai_insight"] is not None
    assert "West" in report_data["ai_insight"]["content"]

    # 10. Invalid input is handled gracefully throughout, not just on the happy path
    bad_upload = client.post("/api/v1/datasets/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert bad_upload.status_code == 422
    missing_dataset = client.get("/api/v1/datasets/does-not-exist/profile")
    assert missing_dataset.status_code == 404
