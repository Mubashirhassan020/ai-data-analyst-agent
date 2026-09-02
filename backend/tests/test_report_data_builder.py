"""Unit tests for report data gathering, against a real uploaded dataset."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db.session import session_factory
from app.main import app
from app.reports.data_builder import build_report_data
from app.storage.factory import get_storage

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_sample() -> str:
    client = TestClient(app)
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    r = client.post("/api/v1/datasets/upload", files={"file": ("sample_sales.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_build_report_data_shape() -> None:
    ds_id = _upload_sample()
    data = build_report_data(session_factory(), get_storage(), ds_id)

    assert data["dataset"]["id"] == ds_id
    assert data["dataset"]["row_count"] == 10
    assert "revenue" in data["executive_summary"] or str(data["profile"]["row_count"]) in data["executive_summary"]
    assert data["profile"]["quality"]["overall"] == 90  # matches Phase 4's verified profile exactly
    assert len(data["numeric_stats"]) >= 1
    assert len(data["categorical_stats"]) >= 1


def test_charts_are_generated_and_capped() -> None:
    ds_id = _upload_sample()
    data = build_report_data(session_factory(), get_storage(), ds_id)
    assert 1 <= len(data["charts"]) <= 4
    for chart in data["charts"]:
        assert chart["image_base64"]
        assert chart["title"]


def test_anomalies_flag_revenue_outliers() -> None:
    ds_id = _upload_sample()
    data = build_report_data(session_factory(), get_storage(), ds_id)
    revenue_anomalies = next((c for c in data["anomalies"]["columns"] if c["column"] == "revenue"), None)
    assert revenue_anomalies is not None
    assert revenue_anomalies["outlier_count"] >= 1


def test_recommendations_reflect_real_issues() -> None:
    ds_id = _upload_sample()
    data = build_report_data(session_factory(), get_storage(), ds_id)
    assert any("revenue" in r for r in data["recommendations"])


def test_no_ai_insight_when_no_chat_session_exists() -> None:
    ds_id = _upload_sample()
    data = build_report_data(session_factory(), get_storage(), ds_id)
    assert data["ai_insight"] is None


def test_ai_insight_present_after_chat_session() -> None:
    from app.db import models

    ds_id = _upload_sample()
    db = session_factory()
    session = models.ChatSession(dataset_id=ds_id)
    db.add(session)
    db.flush()
    db.add(models.ChatMessage(session_id=session.id, role="user", content="hi"))
    db.add(models.ChatMessage(session_id=session.id, role="assistant", content="**Answer:** Revenue is $590 total."))
    db.commit()

    data = build_report_data(session_factory(), get_storage(), ds_id)
    assert data["ai_insight"] is not None
    assert "590" in data["ai_insight"]["content"]


def test_methodology_and_limitations_present() -> None:
    ds_id = _upload_sample()
    data = build_report_data(session_factory(), get_storage(), ds_id)
    assert len(data["methodology"]) > 50
    assert len(data["limitations"]) > 50
