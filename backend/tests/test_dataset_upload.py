from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


def _upload(client: TestClient, filename: str, content: bytes, mime: str) -> dict:
    r = client.post(
        "/api/v1/datasets/upload",
        files={"file": (filename, content, mime)},
    )
    return r


def test_upload_valid_csv() -> None:
    client = TestClient(app)
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    r = _upload(client, "sample_sales.csv", content, "text/csv")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "ready"
    assert body["row_count"] == 10
    assert body["column_count"] == 6
    assert body["original_filename"] == "sample_sales.csv"


def test_upload_rejects_empty_file() -> None:
    client = TestClient(app)
    r = _upload(client, "empty.csv", b"", "text/csv")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_upload_rejects_unsupported_extension() -> None:
    client = TestClient(app)
    r = _upload(client, "malware.exe", b"not a real exe", "application/octet-stream")
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_file"


def test_upload_rejects_malformed_csv_no_columns() -> None:
    client = TestClient(app)
    # A file with only newlines parses to zero columns.
    r = _upload(client, "blank_lines.csv", b"\n\n\n", "text/csv")
    assert r.status_code in (422,)


def test_list_and_get_dataset() -> None:
    client = TestClient(app)
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    created = _upload(client, "sample_sales.csv", content, "text/csv").json()

    listed = client.get("/api/v1/datasets").json()
    assert any(d["id"] == created["id"] for d in listed)

    detail = client.get(f"/api/v1/datasets/{created['id']}").json()
    assert detail["id"] == created["id"]
    assert len(detail["columns"]) == 6
    names = {c["name"] for c in detail["columns"]}
    assert names == {"order_id", "region", "product", "revenue", "units", "order_date"}


def test_get_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/datasets/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_preview_pagination_and_search() -> None:
    client = TestClient(app)
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    created = _upload(client, "sample_sales.csv", content, "text/csv").json()
    ds_id = created["id"]

    page1 = client.get(f"/api/v1/datasets/{ds_id}/preview", params={"page": 1, "page_size": 4}).json()
    assert page1["total_rows"] == 10
    assert page1["total_pages"] == 3
    assert len(page1["rows"]) == 4

    filtered = client.get(
        f"/api/v1/datasets/{ds_id}/preview", params={"search": "West"}
    ).json()
    assert filtered["total_rows"] == 3  # rows with region West

    sorted_desc = client.get(
        f"/api/v1/datasets/{ds_id}/preview",
        params={"sort": "revenue", "sort_dir": "desc", "page_size": 1},
    ).json()
    assert sorted_desc["rows"][0]["order_id"] == 1003  # 241.00 is the max


def test_delete_dataset() -> None:
    client = TestClient(app)
    content = (FIXTURES / "sample_sales.csv").read_bytes()
    created = _upload(client, "sample_sales.csv", content, "text/csv").json()
    ds_id = created["id"]

    r = client.delete(f"/api/v1/datasets/{ds_id}")
    assert r.status_code == 204

    r2 = client.get(f"/api/v1/datasets/{ds_id}")
    assert r2.status_code == 404


def test_upload_excel_file() -> None:
    import io

    import pandas as pd

    client = TestClient(app)
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)

    r = _upload(
        client,
        "sample.xlsx",
        buf.read(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["row_count"] == 3
    assert body["column_count"] == 2
