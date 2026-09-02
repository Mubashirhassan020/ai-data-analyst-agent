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


def test_profile_computes_and_caches() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    ds_id = ds["id"]

    r1 = client.get(f"/api/v1/datasets/{ds_id}/profile")
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["cached"] is False
    assert body1["row_count"] == 10
    assert body1["column_count"] == 6
    assert 0 <= body1["quality"]["overall"] <= 100

    r2 = client.get(f"/api/v1/datasets/{ds_id}/profile")
    body2 = r2.json()
    assert body2["cached"] is True
    assert body2["quality"]["overall"] == body1["quality"]["overall"]


def test_profile_refresh_recomputes() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    ds_id = ds["id"]

    client.get(f"/api/v1/datasets/{ds_id}/profile")
    r = client.get(f"/api/v1/datasets/{ds_id}/profile", params={"refresh": True})
    assert r.json()["cached"] is False


def test_profile_flags_missing_revenue() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    r = client.get(f"/api/v1/datasets/{ds['id']}/profile")
    body = r.json()
    revenue_col = next(c for c in body["columns"] if c["name"] == "revenue")
    assert revenue_col["null_count"] == 1
    assert any(
        i["type"] == "missing_values" and i["column"] == "revenue" for i in body["issues"]
    )


def test_columns_endpoint_upgrades_types_after_profiling() -> None:
    client = TestClient(app)
    ds = _upload_sample(client)
    ds_id = ds["id"]

    # Before profiling: Phase 3 coarse inference treats order_date as text.
    before = client.get(f"/api/v1/datasets/{ds_id}/columns").json()
    order_date_before = next(c for c in before if c["name"] == "order_date")
    assert order_date_before["inferred_type"] == "text"

    client.get(f"/api/v1/datasets/{ds_id}/profile")

    after = client.get(f"/api/v1/datasets/{ds_id}/columns").json()
    order_date_after = next(c for c in after if c["name"] == "order_date")
    assert order_date_after["inferred_type"] == "datetime"
    assert order_date_after["logical_type"] == "date"

    order_id_after = next(c for c in after if c["name"] == "order_id")
    assert order_id_after["logical_type"] == "identifier"

    region_after = next(c for c in after if c["name"] == "region")
    assert region_after["inferred_type"] == "categorical"
    assert region_after["stats"]["categorical"]["distinct_count"] == 4


def test_profile_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/datasets/does-not-exist/profile")
    assert r.status_code == 404
