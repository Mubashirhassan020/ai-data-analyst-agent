"""Classification: Logistic Regression and Random Forest, with train/test split,
weighted precision/recall/F1, ROC-AUC for binary targets, and a confusion matrix."""
from __future__ import annotations

import contextlib
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.core.errors import ValidationError
from app.ml.common import (
    MIN_ROWS,
    build_preprocessor,
    extract_feature_importance,
    split_feature_types,
)

MIN_CLASS_COUNT = 2


def _make_model(algorithm: str, random_state: int):
    if algorithm == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=random_state)
    if algorithm == "random_forest":
        return RandomForestClassifier(n_estimators=200, random_state=random_state)
    raise ValidationError(
        f"Unsupported classification algorithm: {algorithm!r}. "
        "Choose from ['logistic_regression', 'random_forest']."
    )


def train_classifier(
    df: pd.DataFrame,
    *,
    target: str,
    features: list[str],
    algorithm: str = "logistic_regression",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    if target not in df.columns:
        raise ValidationError(f"Unknown target column: {target!r}")
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise ValidationError(f"Unknown feature column(s): {missing}")
    if target in features:
        raise ValidationError("Target column must not also be a feature column.")

    work = df[features + [target]].dropna(subset=[target])
    if len(work) < MIN_ROWS:
        raise ValidationError(f"Not enough rows to train: {len(work)} found, at least {MIN_ROWS} required.")

    class_counts = work[target].value_counts()
    if len(class_counts) < 2:
        raise ValidationError(f"Target {target!r} must have at least 2 classes; found {len(class_counts)}.")
    undersized = class_counts[class_counts < MIN_CLASS_COUNT]
    if not undersized.empty:
        raise ValidationError(
            f"Every class needs at least {MIN_CLASS_COUNT} examples; "
            f"too few for: {undersized.to_dict()}"
        )

    X, y = work[features], work[target]
    numeric_cols, categorical_cols = split_feature_types(X, features)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    model = _make_model(algorithm, random_state)
    pipeline = Pipeline([("prep", build_preprocessor(numeric_cols, categorical_cols)), ("model", model)])
    try:
        pipeline.fit(X_train, y_train)
    except Exception as e:
        raise ValidationError(f"Could not train {algorithm}: {e}") from e

    y_pred = pipeline.predict(X_test)
    classes = list(pipeline.classes_)

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
    }
    if len(classes) == 2 and hasattr(pipeline, "predict_proba"):
        y_proba = pipeline.predict_proba(X_test)[:, 1]
        # e.g. test split ended up single-class; skip rather than fabricate a score
        with contextlib.suppress(ValueError):
            metrics["roc_auc"] = round(float(roc_auc_score(y_test, y_proba)), 4)

    cm = confusion_matrix(y_test, y_pred, labels=classes)

    return {
        "task": "classification",
        "algorithm": algorithm,
        "target": target,
        "features": features,
        "metrics": metrics,
        "confusion_matrix": {"labels": [str(c) for c in classes], "matrix": cm.tolist()},
        "feature_importance": extract_feature_importance(pipeline, numeric_cols, categorical_cols),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
    }
