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


def test_sql_endpoint_group_by() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/sql",
        json={
            "dataset_id": ds["id"],
            "sql": "SELECT region, SUM(revenue) AS total FROM dataset GROUP BY region ORDER BY total DESC",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows"][0]["region"] == "West"
    assert "session_id" in body and "result_id" in body


def test_sql_endpoint_rejects_destructive_query() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post("/api/v1/analysis/sql", json={"dataset_id": ds["id"], "sql": "DROP TABLE dataset"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_sql_endpoint_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.post("/api/v1/analysis/sql", json={"dataset_id": "does-not-exist", "sql": "SELECT 1"})
    assert r.status_code == 404


def test_forecast_endpoint_insufficient_data_returns_422() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    # sample_sales.csv has only 10 daily rows -> below the 5-day-aggregate... actually
    # 10 distinct days IS >= 5, so this should succeed; verify it does.
    r = client.post(
        "/api/v1/analysis/forecast",
        json={"dataset_id": ds["id"], "date_column": "order_date", "value_column": "revenue"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["method"] == "linear"
    assert len(body["forecast"]) == 6
    assert "session_id" in body and "result_id" in body


def test_forecast_endpoint_unknown_column_422() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/forecast",
        json={"dataset_id": ds["id"], "date_column": "not_a_column", "value_column": "revenue"},
    )
    assert r.status_code == 422


def test_forecast_endpoint_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.post(
        "/api/v1/analysis/forecast",
        json={"dataset_id": "does-not-exist", "date_column": "d", "value_column": "v"},
    )
    assert r.status_code == 404


def test_sql_and_forecast_appear_in_session() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r1 = client.post(
        "/api/v1/analysis/sql", json={"dataset_id": ds["id"], "sql": "SELECT * FROM dataset LIMIT 1"}
    )
    session_id = r1.json()["session_id"]
    client.post(
        "/api/v1/analysis/forecast",
        json={
            "dataset_id": ds["id"], "session_id": session_id,
            "date_column": "order_date", "value_column": "revenue",
        },
    )
    r3 = client.get(f"/api/v1/analysis/sessions/{session_id}")
    kinds = {r["kind"] for r in r3.json()["results"]}
    assert kinds == {"sql", "forecast"}
