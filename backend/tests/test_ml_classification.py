"""Unit tests for the classification engine (no DB/HTTP)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.core.errors import ValidationError
from app.ml.classification import train_classifier


def _learnable_df(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    score = rng.normal(0, 1, n)
    label = np.where(score > 0, "yes", "no")
    category = rng.choice(["A", "B"], n)
    return pd.DataFrame({"score": score, "category": category, "label": label})


def test_logistic_regression_learns_separable_pattern() -> None:
    df = _learnable_df()
    result = train_classifier(df, target="label", features=["score", "category"], algorithm="logistic_regression")
    assert result["metrics"]["accuracy"] > 0.8  # score > 0 <=> "yes" is trivially separable
    assert result["metrics"]["roc_auc"] > 0.8
    assert result["confusion_matrix"]["labels"] == sorted(result["confusion_matrix"]["labels"])


def test_random_forest_classifier_runs() -> None:
    df = _learnable_df()
    result = train_classifier(df, target="label", features=["score", "category"], algorithm="random_forest")
    assert result["algorithm"] == "random_forest"
    assert 0 <= result["metrics"]["accuracy"] <= 1


def test_feature_importance_present_and_sums_reasonably() -> None:
    df = _learnable_df()
    result = train_classifier(df, target="label", features=["score", "category"], algorithm="random_forest")
    assert len(result["feature_importance"]) > 0
    names = {f["feature"] for f in result["feature_importance"]}
    assert "score" in names  # numeric feature name preserved through the pipeline


def test_unknown_target_raises() -> None:
    df = _learnable_df()
    with pytest.raises(ValidationError):
        train_classifier(df, target="nope", features=["score"])


def test_unknown_feature_raises() -> None:
    df = _learnable_df()
    with pytest.raises(ValidationError):
        train_classifier(df, target="label", features=["nope"])


def test_target_as_feature_raises() -> None:
    df = _learnable_df()
    with pytest.raises(ValidationError):
        train_classifier(df, target="label", features=["label", "score"])


def test_single_class_target_raises() -> None:
    df = pd.DataFrame({"score": range(20), "label": ["yes"] * 20})
    with pytest.raises(ValidationError):
        train_classifier(df, target="label", features=["score"])


def test_undersized_class_raises() -> None:
    df = pd.DataFrame({"score": range(20), "label": ["yes"] * 19 + ["no"]})
    with pytest.raises(ValidationError):
        train_classifier(df, target="label", features=["score"])


def test_too_few_rows_raises() -> None:
    df = pd.DataFrame({"score": range(6), "label": ["yes", "no"] * 3})
    with pytest.raises(ValidationError):
        train_classifier(df, target="label", features=["score"])


def test_unsupported_algorithm_raises() -> None:
    df = _learnable_df()
    with pytest.raises(ValidationError):
        train_classifier(df, target="label", features=["score"], algorithm="xgboost")


def test_missing_feature_values_handled_via_imputation() -> None:
    df = _learnable_df()
    df.loc[df.index[:5], "score"] = np.nan
    result = train_classifier(df, target="label", features=["score", "category"])
    assert result["train_rows"] + result["test_rows"] == len(df)  # rows kept, imputed not dropped
