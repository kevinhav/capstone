"""Comparison classifiers: alternatives to the nearest-centroid (affinity) baseline, evaluated
with repeated stratified k-fold on identical splits, plus the analyses used to compare them.

Every model is a Pipeline of the shared preprocessor (`build_preprocessor`, z-scored ratios
and one-hot types) and an sklearn classifier, so all models see the same feature space as
the centroids and the preprocessor is refit inside each training fold (no leakage).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

import pandas as pd
from loguru import logger
from sklearn.base import ClassifierMixin, clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from capstone.config import CATEGORICAL, FEATURES, NUMERIC, STYLES, Col, CVConfig
from capstone.features import PREP_STEP, build_preprocessor, feature_names
from capstone.models.centroids import AffinityClassifier

CLASSIFIER_STEP: Final = "clf"
BASELINE: Final = "affinity baseline"
CHANCE: Final = "chance (stratified)"
MAJORITY: Final = "majority class"
METRICS: Final = ("accuracy", "macro_f1", "log_loss")
# the models carried into ablations and per-recipe comparisons (chance and the weaker variants left out)
COMPARED: Final = (BASELINE, "logistic regression", "k-NN (k=3)", "random forest", "SVM (rbf)")
FEATURE_GROUPS: Final[Mapping[str, tuple[Sequence[Col], Sequence[Col]]]] = {
    "all": (NUMERIC, CATEGORICAL),
    "numeric only": (NUMERIC, []),
    "categorical only": ([], CATEGORICAL),
}

_LABELS: Final = [str(s) for s in STYLES]


@dataclass(frozen=True)
class CVResult:
    """Cross-validation output for a set of models evaluated on the same splits.

    folds: one row per (model, repeat, fold) with accuracy, macro_f1 and log_loss.
    preds: one row per (model, repeat, recipe) with the true and predicted style.
    """

    folds: pd.DataFrame
    preds: pd.DataFrame


# -- models and splits ------------------------------------------------------


def _estimators(seed: int) -> dict[str, ClassifierMixin]:
    return {
        CHANCE: DummyClassifier(strategy="stratified", random_state=seed),
        MAJORITY: DummyClassifier(strategy="most_frequent"),
        BASELINE: AffinityClassifier(),
        "logistic regression": LogisticRegression(C=1.0, max_iter=1000),
        "k-NN (k=3)": KNeighborsClassifier(n_neighbors=3),
        "k-NN (k=5)": KNeighborsClassifier(n_neighbors=5),
        "decision tree": DecisionTreeClassifier(max_depth=3, random_state=seed),
        "random forest": RandomForestClassifier(n_estimators=300, random_state=seed),
        # Platt-scaled probabilities, as SVC(probability=True) gave before its deprecation in sklearn 1.9
        "SVM (rbf)": CalibratedClassifierCV(SVC(random_state=seed), method="sigmoid", ensemble=False),
    }


def make_models(
    numeric: Sequence[Col] = NUMERIC,
    categorical: Sequence[Col] = CATEGORICAL,
    *,
    include: Sequence[str] | None = None,
    seed: int = CVConfig.seed,
) -> dict[str, Pipeline]:
    """Unfitted candidate models, each preprocessor + classifier.

    Args:
        numeric, categorical: Feature subsets, for ablations (either may be empty).
        include: Model names to keep, in this order; default all.
        seed: Random state for the stochastic models.
    """
    estimators = _estimators(seed)
    names = list(include) if include is not None else list(estimators)
    unknown = set(names) - set(estimators)
    if unknown:
        raise ValueError(f"unknown models: {sorted(unknown)}")
    return {
        n: Pipeline([(PREP_STEP, build_preprocessor(numeric, categorical)), (CLASSIFIER_STEP, estimators[n])])
        for n in names
    }


def make_cv(config: CVConfig = CVConfig()) -> RepeatedStratifiedKFold:
    """Repeated stratified k-fold splitter from the project's CV settings."""
    return RepeatedStratifiedKFold(n_splits=config.n_splits, n_repeats=config.n_repeats, random_state=config.seed)


# -- cross-validation -------------------------------------------------------


def cross_validate(
    models: Mapping[str, Pipeline],
    X: pd.DataFrame,
    y: pd.Series,
    cv: RepeatedStratifiedKFold | None = None,
) -> CVResult:
    """Fit and score every model on the same folds, keeping per-fold metrics and every
    out-of-fold prediction (so models can be compared pairwise, fold by fold).

    Args:
        models: Name -> unfitted pipeline (cloned per fold, never mutated).
        X: Recipes with the FEATURES columns, indexed by recipe_id.
        y: Style label per recipe.
        cv: Splitter; defaults to `make_cv()`.
    """
    cv = cv or make_cv()
    n_splits = cv.cvargs["n_splits"]
    fold_rows, pred_rows = [], []
    for split, (tr, te) in enumerate(cv.split(X, y)):
        repeat, fold = divmod(split, n_splits)
        y_tr, y_te = y.iloc[tr], y.iloc[te]
        for name, model in models.items():
            m = clone(model).fit(X.iloc[tr], y_tr)
            pred = m.predict(X.iloc[te])
            fold_rows.append({
                "model": name, "repeat": repeat, "fold": fold,
                "accuracy": accuracy_score(y_te, pred),
                "macro_f1": f1_score(y_te, pred, average="macro", labels=_LABELS, zero_division=0),
                "log_loss": log_loss(y_te, m.predict_proba(X.iloc[te]), labels=m.classes_),
            })
            pred_rows.append(pd.DataFrame({
                "model": name, "repeat": repeat, Col.recipe_id.value: X.index[te],
                "true": y_te.to_numpy(), "pred": pred,
            }))
    logger.debug("cross-validated {} models on {} splits", len(models), split + 1)
    preds = pd.concat(pred_rows, ignore_index=True)
    return CVResult(pd.DataFrame(fold_rows), preds.assign(correct=preds["true"] == preds["pred"]))


# -- comparing models -------------------------------------------------------


def model_order(folds: pd.DataFrame, metric: str = "accuracy") -> list[str]:
    """Model names from best to worst mean `metric` (lowest first for log_loss)."""
    means = folds.groupby("model")[metric].mean()
    return list(means.sort_values(ascending=metric == "log_loss").index)


def summarize(folds: pd.DataFrame, metrics: Sequence[str] = METRICS) -> pd.DataFrame:
    """Mean and standard deviation of each metric across all folds, best accuracy first."""
    return folds.groupby("model")[list(metrics)].agg(["mean", "std"]).loc[model_order(folds)]


def repeat_means(folds: pd.DataFrame, metrics: Sequence[str] = ("accuracy", "macro_f1")) -> pd.DataFrame:
    """Each repeat's mean over its folds: the unit that varies independently of how one
    small test fold happened to be drawn, so its spread is the honest uncertainty."""
    return folds.groupby(["model", "repeat"])[list(metrics)].mean().reset_index()


def compare_to_baseline(folds: pd.DataFrame, baseline: str = BASELINE) -> pd.DataFrame:
    """Paired differences from the baseline on identical folds (positive = model better,
    except log loss, where negative is better). The 5-95% range is over repeat means."""
    base = folds[folds["model"] == baseline].set_index(["repeat", "fold"])
    rows = []
    for name in model_order(folds):
        if name == baseline:
            continue
        other = folds[folds["model"] == name].set_index(["repeat", "fold"])
        diff = other["accuracy"] - base["accuracy"]
        per_repeat = diff.groupby("repeat").mean()
        rows.append({
            "model": name,
            "accuracy_diff": diff.mean(),
            "repeat_5pct": per_repeat.quantile(0.05),
            "repeat_95pct": per_repeat.quantile(0.95),
            "folds_better": (diff > 0).mean(),
            "folds_tied": (diff == 0).mean(),
            "folds_worse": (diff < 0).mean(),
            "macro_f1_diff": (other["macro_f1"] - base["macro_f1"]).mean(),
            "log_loss_diff": (other["log_loss"] - base["log_loss"]).mean(),
        })
    return pd.DataFrame(rows).set_index("model")


def per_class_f1(preds: pd.DataFrame) -> pd.DataFrame:
    """F1 for each style (columns) and model (rows), from out-of-fold predictions pooled
    over repeats."""
    return pd.DataFrame({
        name: f1_score(p["true"], p["pred"], labels=_LABELS, average=None, zero_division=0)
        for name, p in preds.groupby("model", sort=False)
    }, index=_LABELS).T


def per_recipe_accuracy(preds: pd.DataFrame, y: pd.Series, models: Sequence[str] = COMPARED) -> pd.DataFrame:
    """Share of repeats in which each model labels each recipe correctly, with the recipe's
    style and the mean over `models`; hardest recipes first."""
    table = preds.pivot_table(index=Col.recipe_id.value, columns="model", values="correct", aggfunc="mean")
    table = table[[m for m in models if m in table.columns]]
    table.insert(0, Col.style.value, y.reindex(table.index))
    return table.assign(mean_compared=table[list(table.columns[1:])].mean(axis=1)).sort_values("mean_compared")


def confused_as(preds: pd.DataFrame, recipe_ids: Sequence[str], models: Sequence[str] = COMPARED) -> pd.DataFrame:
    """For the given recipes, the share of `models`' predictions going to each style,
    i.e. what the models think a misclassified recipe actually is."""
    p = preds[preds[Col.recipe_id.value].isin(recipe_ids) & preds["model"].isin(models)]
    return p.groupby([Col.recipe_id.value, "true"])["pred"].value_counts(normalize=True).unstack(fill_value=0)


def model_agreement(preds: pd.DataFrame, models: Sequence[str] = COMPARED) -> dict[str, float]:
    """Over every (repeat, recipe): how often all `models` predict the same style, and how
    often they all match the label."""
    p = preds[preds["model"].isin(models)]
    g = p.groupby(["repeat", Col.recipe_id.value]).agg(n_unique=("pred", "nunique"), all_correct=("correct", "all"))
    return {"all_agree": float((g["n_unique"] == 1).mean()), "all_correct": float(g["all_correct"].mean())}


# -- what carries the signal ------------------------------------------------


def feature_group_ablation(
    X: pd.DataFrame,
    y: pd.Series,
    cv: RepeatedStratifiedKFold | None = None,
    *,
    models: Sequence[str] = COMPARED,
    groups: Mapping[str, tuple[Sequence[Col], Sequence[Col]]] = FEATURE_GROUPS,
    metrics: Sequence[str] = ("accuracy", "macro_f1"),
) -> pd.DataFrame:
    """Mean CV metrics with each feature group alone (e.g. numeric only vs categorical only).
    Columns are (group, metric); rows are models."""
    out = {}
    for name, (numeric, categorical) in groups.items():
        res = cross_validate(make_models(numeric, categorical, include=models), X, y, cv)
        out[name] = res.folds.groupby("model")[list(metrics)].mean()
    return pd.concat(out, axis=1).loc[list(models)]


def drop_one_feature(
    X: pd.DataFrame,
    y: pd.Series,
    cv: RepeatedStratifiedKFold | None = None,
    *,
    models: Sequence[str] = COMPARED,
    metric: str = "accuracy",
) -> pd.DataFrame:
    """Change in mean CV `metric` when each feature is removed (rows) for each model
    (columns), relative to all features. Negative = the model relies on that feature."""
    def score(numeric: Sequence[Col], categorical: Sequence[Col]) -> pd.Series:
        res = cross_validate(make_models(numeric, categorical, include=models), X, y, cv)
        return res.folds.groupby("model")[metric].mean()

    full = score(NUMERIC, CATEGORICAL)
    rows = {
        str(f): score([c for c in NUMERIC if c != f], [c for c in CATEGORICAL if c != f]) - full
        for f in FEATURES
    }
    return pd.DataFrame(rows).T[list(models)]


# -- interpretation ---------------------------------------------------------


def logistic_coefficients(pipe: Pipeline) -> pd.DataFrame:
    """Coefficients of a fitted logistic-regression pipeline: one row per transformed
    feature, one column per style, largest absolute effect first. Numeric features are in
    z-units, so their coefficients are comparable with each other."""
    clf = pipe[CLASSIFIER_STEP]
    coef = pd.DataFrame(clf.coef_, index=clf.classes_, columns=feature_names(pipe)).T
    return coef.loc[coef.abs().max(axis=1).sort_values(ascending=False).index]


def cv_permutation_importance(
    model: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    cv: RepeatedStratifiedKFold | None = None,
    *,
    n_repeats: int = 10,
    seed: int = CVConfig.seed,
    scoring: str = "accuracy",
) -> pd.DataFrame:
    """Held-out permutation importance: for each fold, the drop in `scoring` on the test
    fold when one raw feature is shuffled. Rows are X's columns, columns are folds; summarize
    with .mean(axis=1) and .std(axis=1)."""
    cv = cv or make_cv(CVConfig(n_repeats=5))
    cols = {}
    for split, (tr, te) in enumerate(cv.split(X, y)):
        m = clone(model).fit(X.iloc[tr], y.iloc[tr])
        r = permutation_importance(m, X.iloc[te], y.iloc[te], n_repeats=n_repeats, random_state=seed, scoring=scoring)
        cols[split] = r.importances_mean
    return pd.DataFrame(cols, index=[str(c) for c in X.columns])
