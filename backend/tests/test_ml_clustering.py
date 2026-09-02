"""Unit tests for K-Means clustering (no DB/HTTP)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.core.errors import ValidationError
from app.ml.clustering import train_clustering


def _two_blob_df() -> pd.DataFrame:
    rng = np.random.default_rng(5)
    blob_a = rng.normal(loc=[0, 0], scale=0.3, size=(30, 2))
    blob_b = rng.normal(loc=[10, 10], scale=0.3, size=(30, 2))
    data = np.vstack([blob_a, blob_b])
    return pd.DataFrame({"x": data[:, 0], "y": data[:, 1]})


def test_kmeans_finds_two_well_separated_blobs() -> None:
    df = _two_blob_df()
    result = train_clustering(df, features=["x", "y"], n_clusters=2)
    assert result["metrics"]["silhouette_score"] > 0.8  # blobs are far apart -> near-perfect separation
    sizes = result["cluster_sizes"]
    assert sorted(sizes.values()) == [30, 30]


def test_cluster_sizes_sum_to_rows_used() -> None:
    df = _two_blob_df()
    result = train_clustering(df, features=["x", "y"], n_clusters=2)
    assert sum(result["cluster_sizes"].values()) == result["rows_used"]


def test_centroids_shape_matches_features() -> None:
    df = _two_blob_df()
    result = train_clustering(df, features=["x", "y"], n_clusters=2)
    assert len(result["centroids"]) == 2
    assert all(len(c) == 2 for c in result["centroids"])


def test_non_numeric_feature_raises() -> None:
    df = pd.DataFrame({"x": range(20), "label": ["a", "b"] * 10})
    with pytest.raises(ValidationError):
        train_clustering(df, features=["x", "label"], n_clusters=2)


def test_too_few_rows_raises() -> None:
    df = pd.DataFrame({"x": range(5), "y": range(5)})
    with pytest.raises(ValidationError):
        train_clustering(df, features=["x", "y"], n_clusters=2)


def test_n_clusters_out_of_range_raises() -> None:
    df = _two_blob_df()
    with pytest.raises(ValidationError):
        train_clustering(df, features=["x", "y"], n_clusters=1)
    with pytest.raises(ValidationError):
        train_clustering(df, features=["x", "y"], n_clusters=100)


def test_unknown_feature_raises() -> None:
    df = _two_blob_df()
    with pytest.raises(ValidationError):
        train_clustering(df, features=["nope"], n_clusters=2)
