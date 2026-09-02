from fastapi.testclient import TestClient

from app.main import app


def test_health_ok() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["llm_configured"] is False
    assert body["db"]["ok"] is True
    assert body["storage"]["writable"] is True


def test_request_id_header_echoed() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/health", headers={"X-Request-ID": "test-req-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "test-req-123"


def test_request_id_generated_when_absent() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.headers.get("X-Request-ID")  # non-empty
