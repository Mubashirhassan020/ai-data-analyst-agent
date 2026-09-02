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


def test_chart_bar_by_region() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/chart",
        json={
            "dataset_id": ds["id"], "chart_type": "bar",
            "x": "region", "y": "revenue", "aggregation": "sum",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chart_type"] == "bar"
    assert "session_id" in body and "result_id" in body
    trace = body["data"][0]
    west_idx = trace["x"].index("West")
    assert trace["y"][west_idx] == 361.5


def test_chart_line_time_series() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/chart",
        json={"dataset_id": ds["id"], "chart_type": "line", "x": "order_date", "y": "revenue"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["granularity"] == "D"


def test_chart_heatmap() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/chart",
        json={"dataset_id": ds["id"], "chart_type": "heatmap", "columns": ["revenue", "units"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"][0]["type"] == "heatmap"


def test_chart_invalid_type_returns_422() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post(
        "/api/v1/analysis/chart",
        json={"dataset_id": ds["id"], "chart_type": "not_a_type", "x": "region"},
    )
    assert r.status_code == 422


def test_chart_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.post(
        "/api/v1/analysis/chart",
        json={"dataset_id": "does-not-exist", "chart_type": "bar", "x": "region"},
    )
    assert r.status_code == 404


def test_eda_suggestions_endpoint() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.get(f"/api/v1/datasets/{ds['id']}/eda-suggestions")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dataset_id"] == ds["id"]
    assert len(body["charts"]) > 0
    for chart in body["charts"]:
        assert "reason" in chart and chart["reason"]
        assert "data" in chart and chart["data"]


def test_eda_suggestions_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/datasets/does-not-exist/eda-suggestions")
    assert r.status_code == 404
