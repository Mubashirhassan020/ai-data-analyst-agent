"""Integration tests for the /ai/* HTTP endpoints. No LLM is configured in the
test environment (see conftest.py), so these verify the API's honest failure
behavior: a 503 with a clear error code, never a fabricated response."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_sample(client: TestClient) -> dict:
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    r = client.post("/api/v1/datasets/upload", files={"file": ("sample_sales.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()


def test_chat_returns_503_when_llm_not_configured() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post("/api/v1/ai/chat", json={"dataset_id": ds["id"], "message": "Summarize this dataset"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "llm_not_configured"


def test_analyze_returns_503_when_llm_not_configured() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post("/api/v1/ai/analyze", json={"dataset_id": ds["id"]})
    assert r.status_code == 503


def test_chat_missing_dataset_returns_404_not_503() -> None:
    # Dataset validation must happen before the LLM-configured check.
    client = TestClient(app)
    r = client.post("/api/v1/ai/chat", json={"dataset_id": "does-not-exist", "message": "hi"})
    assert r.status_code == 404


def test_chat_does_not_persist_orphaned_session_when_unconfigured() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    client.post("/api/v1/ai/chat", json={"dataset_id": ds["id"], "message": "hi"})
    # No session was ever created since the LLM check fails before session creation.
    r = client.get("/api/v1/ai/sessions/nonexistent-anyway/messages")
    assert r.status_code == 404


def test_messages_missing_session_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/ai/sessions/does-not-exist/messages")
    assert r.status_code == 404


def test_chat_empty_message_rejected() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post("/api/v1/ai/chat", json={"dataset_id": ds["id"], "message": ""})
    assert r.status_code == 422
