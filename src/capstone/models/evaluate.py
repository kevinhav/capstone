"""Quantitative evaluation of the recipe adjuster on real recipes.

Every real recipe not of a target style is adjusted toward that style, then judged by:
whether its nearest centroid becomes the target (the adjuster's own criterion), whether
independent classifiers trained out of fold agree, how far it moved toward the target
centroid, how close it ends to a real recipe of the target style, and how much it changed.
"""

from collections.abc import Sequence
from typing import Final

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.base import clone
from sklearn.metrics import pairwise_distances
from sklearn.model_selection import StratifiedKFold

from capstone.config import FEATURES, LossWeights, Col, CVConfig, Style
from capstone.features import transform
from capstone.models.adjust import CHANGE_COUNTS, DISTANCE_AFTER, DISTANCE_BEFORE, SearchSpace, adjust_many
from capstone.models.centroids import distances, predict
from capstone.models.classify import make_models

JUDGES: Final = ("random forest", "logistic regression", "SVM (rbf)")

N_RECIPES: Final = "n_recipes"
TARGET_BEFORE: Final = "target_before"
SUCCESS: Final = "success"
SUCCESS_LO: Final = "success_ci_low"
SUCCESS_HI: Final = "success_ci_high"
NEAREST_BEFORE: Final = "nearest_real_before"
NEAREST_AFTER: Final = "nearest_real_after"
NEAREST_REFERENCE: Final = "nearest_real_reference"


def judge_column(name: str) -> str:
    """Column of `evaluate_adjustments` holding judge `name`'s agreement with the target."""
    return f"judge_{name}"


def _judge_out_of_fold(
    recipes: pd.DataFrame,
    adjusted: dict[str, pd.DataFrame],
    judges: Sequence[str],
    config: CVConfig,
) -> dict[str, dict[str, pd.Series]]:
    """Each judge's prediction for every adjusted recipe, from a model fit on the folds
    that exclude the original recipe, so no judge has seen the recipe it is judging."""
    y = recipes[Col.style]
    preds: dict[str, dict[str, list[pd.Series]]] = {t: {j: [] for j in judges} for t in adjusted}
    folds = StratifiedKFold(n_splits=config.n_splits, shuffle=True, random_state=config.seed)
    for tr, te in folds.split(recipes, y):
        test_ids = recipes.index[te]
        for name, model in make_models(include=judges, seed=config.seed).items():
            fitted = clone(model).fit(recipes.iloc[tr][FEATURES], y.iloc[tr])
            for target, frame in adjusted.items():
                ids = frame.index.intersection(test_ids)
                if len(ids):
                    preds[target][name].append(pd.Series(fitted.predict(frame.loc[ids, FEATURES]), index=ids))
    return {t: {j: pd.concat(p) for j, p in by_judge.items()} for t, by_judge in preds.items()}


def _bootstrap_ci(hits: np.ndarray, n_boot: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = [hits[rng.integers(0, len(hits), len(hits))].mean() for _ in range(n_boot)]
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _nearest_real(space: SearchSpace, X: pd.DataFrame, reference: pd.DataFrame) -> np.ndarray:
    """Distance from each recipe in X to its nearest recipe in `reference`, in feature space."""
    return pairwise_distances(transform(space.pipe, X), transform(space.pipe, reference)).min(axis=1)


def _reference_spacing(space: SearchSpace, reference: pd.DataFrame) -> float:
    """Mean distance from each reference recipe to its nearest other reference recipe:
    how close real recipes of a style typically sit to one another."""
    d = pairwise_distances(transform(space.pipe, reference))
    np.fill_diagonal(d, np.inf)
    return float(d.min(axis=1).mean())


def evaluate_adjustments(
    recipes: pd.DataFrame,
    space: SearchSpace,
    targets: Sequence[Style | str],
    *,
    weights: LossWeights = LossWeights(),
    judges: Sequence[str] = JUDGES,
    config: CVConfig = CVConfig(),
    n_boot: int = 1000,
) -> pd.DataFrame:
    """Adjust every real recipe not of each target style toward it and score the result.

    Args:
        recipes: Real recipes with FEATURES and the style column.
        space: Search space of the fitted centroid pipeline (see `build_search_space`).
        targets: Styles to adjust toward.
        weights: Loss weights for the adjuster.
        judges: Names from `make_models` used as independent classifiers, each fit out of fold.
        config: Fold count and seed for the judges and the bootstrap.
        n_boot: Bootstrap resamples for the success-rate interval.

    Returns:
        One row per target. Columns: N_RECIPES; TARGET_BEFORE and SUCCESS, the share whose
        nearest centroid is the target before and after, with a 95% bootstrap interval
        (SUCCESS_LO, SUCCESS_HI); `judge_column(j)`, the share each judge labels the target;
        mean distance to the target centroid before and after; mean distance to the nearest
        real recipe of the target style before and after, with NEAREST_REFERENCE, the
        typical spacing between real recipes of that style; and the mean of each CHANGE_COUNTS.
    """
    style = recipes[Col.style]
    sources = {str(t): recipes[style != t] for t in targets}
    runs = {t: adjust_many(src, t, space, weights) for t, src in sources.items()}
    verdicts = _judge_out_of_fold(recipes, {t: adjusted for t, (adjusted, _) in runs.items()}, judges, config)

    rows = {}
    for t, src in sources.items():
        adjusted, info = runs[t]
        reference = recipes[style == t]
        hits = (predict(space.pipe, adjusted) == t).to_numpy()
        lo, hi = _bootstrap_ci(hits, n_boot, config.seed)
        rows[t] = {
            N_RECIPES: len(src),
            TARGET_BEFORE: float((predict(space.pipe, src) == t).mean()),
            SUCCESS: float(hits.mean()),
            SUCCESS_LO: lo,
            SUCCESS_HI: hi,
            **{judge_column(j): float((verdicts[t][j].reindex(src.index) == t).mean()) for j in judges},
            DISTANCE_BEFORE: float(distances(space.pipe, src)[t].mean()),
            DISTANCE_AFTER: float(distances(space.pipe, adjusted)[t].mean()),
            NEAREST_BEFORE: float(_nearest_real(space, src, reference).mean()),
            NEAREST_AFTER: float(_nearest_real(space, adjusted, reference).mean()),
            NEAREST_REFERENCE: _reference_spacing(space, reference),
            **info[list(CHANGE_COUNTS)].mean().to_dict(),
        }
    logger.debug("evaluated adjustments toward {}", list(sources))
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis(Col.style.value)
