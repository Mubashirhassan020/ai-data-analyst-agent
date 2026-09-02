from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_sample(client: TestClient) -> dict:
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    r = client.post("/api/v1/datasets/upload", files={"file": ("sample_sales.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()


def test_generate_html_report() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post("/api/v1/reports/generate", json={"dataset_id": ds["id"], "format": "html"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["format"] == "html"
    assert body["dataset_id"] == ds["id"]
    assert len(body["sections"]) == 10


def test_download_html_report_contains_real_data() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    report = client.post("/api/v1/reports/generate", json={"dataset_id": ds["id"], "format": "html"}).json()

    r = client.get(f"/api/v1/reports/{report['id']}/download")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    html = r.text
    assert "sample_sales.csv" in html
    assert "90/100" in html  # the verified quality score for this fixture


def test_generate_json_report_is_valid_json_with_real_numbers() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    report = client.post("/api/v1/reports/generate", json={"dataset_id": ds["id"], "format": "json"}).json()

    r = client.get(f"/api/v1/reports/{report['id']}/download")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = json.loads(r.content)
    assert data["dataset"]["row_count"] == 10
    assert data["profile"]["quality"]["overall"] == 90


def test_generate_pdf_report_succeeds_or_fails_cleanly() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.post("/api/v1/reports/generate", json={"dataset_id": ds["id"], "format": "pdf"})
    # Environment-dependent: WeasyPrint needs system libs present in Docker but
    # commonly missing on a bare Windows dev box. Both outcomes are correct.
    assert r.status_code in (201, 503)
    if r.status_code == 503:
        assert r.json()["error"]["code"] == "pdf_unavailable"
    else:
        report = r.json()
        download = client.get(f"/api/v1/reports/{report['id']}/download")
        assert download.headers["content-type"] == "application/pdf"
        assert download.content[:4] == b"%PDF"


def test_generate_report_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.post("/api/v1/reports/generate", json={"dataset_id": "does-not-exist", "format": "html"})
    assert r.status_code == 404


def test_get_report_metadata() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    report = client.post("/api/v1/reports/generate", json={"dataset_id": ds["id"], "format": "html"}).json()

    r = client.get(f"/api/v1/reports/{report['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == report["id"]


def test_get_report_missing_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/reports/does-not-exist")
    assert r.status_code == 404


def test_download_missing_report_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/reports/does-not-exist/download")
    assert r.status_code == 404
