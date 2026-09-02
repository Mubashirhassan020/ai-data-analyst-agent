from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_sample(client: TestClient) -> dict:
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    r = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample_sales.csv", content, "text/csv")},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_execute_group_by_region_highest_revenue() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)

    r = client.post(
        "/api/v1/analysis/execute",
        json={
            "dataset_id": ds["id"],
            "group_by": ["region"],
            "metrics": [{"aggregation": "sum", "column": "revenue", "alias": "total_revenue"}],
            "sort": {"by": "total_revenue", "direction": "desc"},
            "limit": 1,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] == 1
    assert body["rows"][0]["region"] == "West"  # West: 120.50+241.00 = 361.50 (row 1007 has null revenue)
    assert "session_id" in body and "result_id" in body


def test_execute_filters_raw_rows() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)

    r = client.post(
        "/api/v1/analysis/execute",
        json={"dataset_id": ds["id"], "filters": [{"column": "region", "operator": "eq", "value": "East"}]},
    )
    body = r.json()
    assert body["row_count"] == 3
    assert all(row["region"] == "East" for row in body["rows"])


def test_execute_reuses_session() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)

    r1 = client.post(
        "/api/v1/analysis/execute",
        json={"dataset_id": ds["id"], "group_by": ["region"], "metrics": [{"aggregation": "count"}]},
    )
    session_id = r1.json()["session_id"]

    r2 = client.post(
        "/api/v1/analysis/execute",
        json={
            "dataset_id": ds["id"],
            "session_id": session_id,
            "group_by": ["product"],
            "metrics": [{"aggregation": "count"}],
        },
    )
    assert r2.json()["session_id"] == session_id

    r3 = client.get(f"/api/v1/analysis/sessions/{session_id}")
    assert r3.status_code == 200
    assert len(r3.json()["results"]) == 2


def test_execute_invalid_column_returns_422() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/execute",
        json={"dataset_id": ds["id"], "group_by": ["not_a_column"]},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_execute_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.post("/api/v1/analysis/execute", json={"dataset_id": "does-not-exist"})
    assert r.status_code == 404


def test_correlation_endpoint() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/correlation",
        json={"dataset_id": ds["id"], "columns": ["revenue", "units"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["columns"] == ["revenue", "units"]
    assert len(body["matrix"]) == 2


def test_outliers_endpoint_flags_revenue() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/outliers",
        json={"dataset_id": ds["id"], "columns": ["revenue"], "method": "iqr"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["columns"][0]["column"] == "revenue"
    assert body["columns"][0]["outlier_count"] >= 1


def test_session_not_found_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/analysis/sessions/does-not-exist")
    assert r.status_code == 404


def test_metric_requires_column_unless_count() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/execute",
        json={"dataset_id": ds["id"], "metrics": [{"aggregation": "sum"}]},
    )
    assert r.status_code == 422
