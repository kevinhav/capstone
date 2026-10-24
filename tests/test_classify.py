"""Comparison classifiers and the CV analyses built on them."""

import pandas as pd
import pytest
from sklearn.model_selection import RepeatedStratifiedKFold

from capstone.config import FEATURES, NUMERIC, Col
from capstone.data import load_recipes
from capstone.models import (
    BASELINE,
    compare_to_baseline,
    cross_validate,
    logistic_coefficients,
    make_models,
    model_agreement,
    per_class_f1,
    per_recipe_accuracy,
    summarize,
)

MODELS = [BASELINE, "logistic regression"]


@pytest.fixture(scope="module")
def data():
    df = load_recipes()
    return df[FEATURES], df[Col.style]


@pytest.fixture(scope="module")
def result(data):
    X, y = data
    cv = RepeatedStratifiedKFold(n_splits=3, n_repeats=2, random_state=0)
    return cross_validate(make_models(include=MODELS), X, y, cv)


def test_make_models_filters_and_validates_names():
    assert list(make_models(include=MODELS)) == MODELS
    assert BASELINE in make_models()
    with pytest.raises(ValueError):
        make_models(include=["no such model"])


def test_make_models_supports_feature_subsets(data):
    X, y = data
    pipe = make_models(NUMERIC, [], include=["logistic regression"])["logistic regression"].fit(X, y)
    assert logistic_coefficients(pipe).shape == (len(NUMERIC), 3)


def test_every_recipe_is_predicted_once_per_repeat(result, data):
    X, _ = data
    assert len(result.folds) == len(MODELS) * 3 * 2
    counts = result.preds.groupby(["model", "repeat"])[Col.recipe_id.value].nunique()
    assert (counts == len(X)).all()
    assert result.preds["correct"].equals(result.preds["true"] == result.preds["pred"])


def test_summaries(result, data):
    _, y = data
    table = summarize(result.folds)
    assert set(table.index) == set(MODELS)
    assert ((table[("accuracy", "mean")] >= 0) & (table[("accuracy", "mean")] <= 1)).all()
    assert list(per_class_f1(result.preds).columns) == ["neapolitan", "new-york", "sicilian"]
    per_recipe = per_recipe_accuracy(result.preds, y, MODELS)
    assert per_recipe["mean_compared"].is_monotonic_increasing
    agreement = model_agreement(result.preds, MODELS)
    assert 0 <= agreement["all_correct"] <= agreement["all_agree"] <= 1


def test_compare_to_baseline_is_paired():
    folds = pd.DataFrame({
        "model": [BASELINE, BASELINE, "copy", "copy", "better", "better"],
        "repeat": [0, 0, 0, 0, 0, 0],
        "fold": [0, 1, 0, 1, 0, 1],
        "accuracy": [0.5, 0.7, 0.5, 0.7, 0.6, 0.8],
        "macro_f1": [0.5, 0.7, 0.5, 0.7, 0.6, 0.8],
        "log_loss": [1.0, 1.0, 1.0, 1.0, 0.9, 0.9],
    })
    diff = compare_to_baseline(folds)
    assert BASELINE not in diff.index
    assert diff.loc["copy", "accuracy_diff"] == 0
    assert diff.loc["copy", "folds_tied"] == 1
    assert diff.loc["better", "accuracy_diff"] == pytest.approx(0.1)
    assert diff.loc["better", "folds_better"] == 1
