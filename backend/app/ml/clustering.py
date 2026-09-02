"""Clustering: K-Means over numeric features, with silhouette score and cluster
sizes. Restricted to numeric columns — mixing one-hot-encoded categorical
distances with scaled numeric distances muddies K-Means' Euclidean-distance
assumption, so categorical clustering is left out rather than done poorly."""
from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from app.analytics.common import json_safe
from app.core.errors import ValidationError
from app.ml.common import MIN_ROWS

MAX_CLUSTERS = 20


def train_clustering(
    df: pd.DataFrame,
    *,
    features: list[str],
    n_clusters: int = 3,
    random_state: int = 42,
) -> dict[str, Any]:
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise ValidationError(f"Unknown feature column(s): {missing}")
    non_numeric = [f for f in features if not pd.api.types.is_numeric_dtype(df[f])]
    if non_numeric:
        raise ValidationError(f"Clustering requires numeric columns; not numeric: {non_numeric}")

    work = df[features].dropna()
    if len(work) < MIN_ROWS:
        raise ValidationError(f"Not enough rows to cluster: {len(work)} found, at least {MIN_ROWS} required.")
    if n_clusters < 2 or n_clusters > min(MAX_CLUSTERS, len(work) // 2):
        raise ValidationError(
            f"n_clusters must be between 2 and {min(MAX_CLUSTERS, len(work) // 2)} for {len(work)} rows."
        )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(work)

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    try:
        labels = model.fit_predict(X_scaled)
    except Exception as e:
        raise ValidationError(f"Could not fit K-Means: {e}") from e

    silhouette = None
    if 1 < n_clusters < len(work):
        silhouette = round(float(silhouette_score(X_scaled, labels)), 4)

    cluster_sizes = pd.Series(labels).value_counts().sort_index()
    centroids = scaler.inverse_transform(model.cluster_centers_)

    return {
        "task": "clustering",
        "algorithm": "kmeans",
        "features": features,
        "metrics": {"silhouette_score": silhouette},
        "cluster_sizes": {str(k): int(v) for k, v in cluster_sizes.items()},
        "centroids": [[json_safe(v) for v in row] for row in centroids],
        "rows_used": int(len(work)),
    }
