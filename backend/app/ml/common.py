"""Shared ML plumbing: preprocessing pipeline and feature-importance extraction.

Feature importance uses each model's own native signal — Gini importance for
tree ensembles, |coefficient| for linear/logistic models — rather than SHAP.
SHAP is a heavier, more fragile dependency (native-extension build issues,
slow on wide one-hot-encoded feature spaces) for marginal benefit over a
model's own importances on the small-to-mid datasets this app targets. This
function is the swap-in point if SHAP is added later.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.core.errors import ValidationError

# Below this row count, a train/test split (or an unsupervised fit) isn't
# meaningful — refuse rather than force a result on too little data.
MIN_ROWS = 10

MAX_FEATURE_IMPORTANCES = 15


def build_preprocessor(numeric_cols: list[str], categorical_cols: list[str]) -> ColumnTransformer:
    transformers = []
    if numeric_cols:
        transformers.append((
            "num",
            Pipeline([("impute", SimpleImputer(strategy="mean")), ("scale", StandardScaler())]),
            numeric_cols,
        ))
    if categorical_cols:
        transformers.append((
            "cat",
            Pipeline([
                ("impute", SimpleImputer(strategy="most_frequent")),
                ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]),
            categorical_cols,
        ))
    if not transformers:
        raise ValidationError("No usable feature columns (need at least one numeric or categorical column).")
    return ColumnTransformer(transformers)


def _clean_feature_name(name: str) -> str:
    # ColumnTransformer prefixes names like "num__age" / "cat__region_West".
    return name.split("__", 1)[-1] if "__" in name else name


def extract_feature_importance(pipeline: Pipeline, numeric_cols: list[str], categorical_cols: list[str]) -> list[dict[str, Any]]:
    model = pipeline.named_steps["model"]
    try:
        feature_names = list(pipeline.named_steps["prep"].get_feature_names_out())
    except Exception:  # noqa: BLE001 - fall back to raw column names if encoding introspection fails
        feature_names = numeric_cols + categorical_cols

    if hasattr(model, "feature_importances_"):
        raw = np.asarray(model.feature_importances_)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_)
        raw = np.abs(coef[0]) if coef.ndim > 1 else np.abs(coef)
    else:
        return []

    if len(raw) != len(feature_names):
        return []

    pairs = sorted(zip(feature_names, raw, strict=True), key=lambda p: -p[1])
    total = float(sum(v for _, v in pairs)) or 1.0
    return [
        {
            "feature": _clean_feature_name(name),
            "importance": round(float(v), 4),
            "importance_pct": round(100 * float(v) / total, 2),
        }
        for name, v in pairs[:MAX_FEATURE_IMPORTANCES]
    ]


def split_feature_types(df: pd.DataFrame, features: list[str]) -> tuple[list[str], list[str]]:
    numeric_cols = [c for c in features if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in features if c not in numeric_cols]
    return numeric_cols, categorical_cols
