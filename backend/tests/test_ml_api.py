from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_ml_sample(client: TestClient) -> dict:
    content = (FIXTURES / "ml_sample.csv").read_bytes()
    r = client.post("/api/v1/datasets/upload", files={"file": ("ml_sample.csv", content, "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()


def test_suggest_endpoint_returns_viable_tasks() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    r = client.post("/api/v1/ml/suggest", json={"dataset_id": ds["id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    tasks = {s["task"] for s in body["suggestions"]}
    assert "classification" in tasks
    assert "regression" in tasks


def test_suggest_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.post("/api/v1/ml/suggest", json={"dataset_id": "does-not-exist"})
    assert r.status_code == 404


def test_train_classification_via_api() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    r = client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": ds["id"], "task": "classification", "target": "purchased",
            "features": ["age", "income", "region"], "algorithm": "logistic_regression",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["task"] == "classification"
    assert 0 <= body["metrics"]["accuracy"] <= 1
    assert body["confusion_matrix"] is not None
    assert len(body["feature_importance"]) > 0
    assert body["model_id"]


def test_train_regression_via_api() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    r = client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": ds["id"], "task": "regression", "target": "spend",
            "features": ["age", "income", "region"], "algorithm": "random_forest",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["task"] == "regression"
    assert "r2" in body["metrics"]
    assert body["metrics"]["r2"] > 0.5  # spend is constructed to correlate with income


def test_train_clustering_via_api() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    r = client.post(
        "/api/v1/ml/train",
        json={"dataset_id": ds["id"], "task": "clustering", "features": ["age", "income"], "n_clusters": 3},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cluster_sizes"] is not None
    assert sum(body["cluster_sizes"].values()) == body["rows_used"]


def test_train_anomaly_detection_via_api() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    r = client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": ds["id"], "task": "anomaly_detection",
            "features": ["age", "income"], "contamination": 0.1,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metrics"]["anomaly_count"] >= 1
    assert body["sample_rows"] is not None


def test_train_classification_without_target_returns_422() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    r = client.post(
        "/api/v1/ml/train",
        json={"dataset_id": ds["id"], "task": "classification", "features": ["age"]},
    )
    assert r.status_code == 422


def test_train_target_as_feature_returns_422() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    r = client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": ds["id"], "task": "classification", "target": "purchased",
            "features": ["purchased", "age"],
        },
    )
    assert r.status_code == 422


def test_train_missing_dataset_404() -> None:
    client = TestClient(app)
    r = client.post(
        "/api/v1/ml/train",
        json={"dataset_id": "does-not-exist", "task": "regression", "target": "y", "features": ["x"]},
    )
    assert r.status_code == 404


def test_get_model_results_roundtrip() -> None:
    client = TestClient(app)
    ds = _upload_ml_sample(client)
    train_resp = client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": ds["id"], "task": "regression", "target": "spend",
            "features": ["age", "income"], "algorithm": "linear_regression",
        },
    ).json()

    r = client.get(f"/api/v1/ml/{train_resp['model_id']}/results")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_id"] == train_resp["model_id"]
    assert body["metrics"] == train_resp["metrics"]


def test_get_model_results_missing_404() -> None:
    client = TestClient(app)
    r = client.get("/api/v1/ml/does-not-exist/results")
    assert r.status_code == 404
