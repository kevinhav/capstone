"""Sensitivity of the classifiers and the recipe adjuster to their weights.

Three questions, each answered on the real recipes:

- `addition_gains`: how much adding each optional ingredient is worth toward each target.
  The loss separates by feature and every recipe lacking an ingredient encodes it the
  same way, so the gain is one number per (target, ingredient): an ingredient is added
  exactly when its gain exceeds the fixed add cost, for every such recipe at once.
- `penalty_sensitivity`: adjustment results as each change penalty is scaled one at a
  time, and with additions switched off.
- `type_weight_sensitivity`: classifier accuracy and adjustment results as the weight
  on the one-hot type columns changes relative to the z-scored ratios.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass, fields, replace
from typing import Final

import pandas as pd
from loguru import logger

from capstone.config import FEATURES, OPTIONAL, Col, CVConfig, LossWeights, Style
from capstone.models.adjust import CHANGE_COUNTS, ENRICHMENTS, SearchSpace, adjust_many, build_search_space
from capstone.models.centroids import fit_centroids
from capstone.models.classify import BASELINE, cross_validate, make_cv, make_models, repeat_means
from capstone.models.evaluate import JUDGES, SUCCESS, evaluate_adjustments, judge_column

# columns of the returned frames
TARGET: Final = "target"
INGREDIENT: Final = "ingredient"
N_LACKING: Final = "n_lacking"
NET_GAIN: Final = "net_gain"
GAIN_SPREAD: Final = "gain_spread"
PARAMETER: Final = "parameter"
VALUE: Final = "value"
JUDGE_MEAN: Final = "judge_mean"
TYPE_WEIGHT: Final = "type_weight"
ACCURACY: Final = "accuracy"
ACCURACY_SD: Final = "accuracy_repeat_sd"

# parameter names of the rows that are not a scaled LossWeights field
DEFAULT: Final = "default"
ADDABLE: Final = "addable"

# models whose CV accuracy depends on the type weight (trees are invariant to column scaling)
WEIGHT_SENSITIVE_MODELS: Final = (BASELINE, "k-NN (k=3)", "logistic regression", "SVM (rbf)")


@dataclass(frozen=True)
class AdjusterSetting:
    """One configuration of the adjuster to evaluate: the row's parameter and value, the
    loss weights, and the ingredients it may add."""

    parameter: str
    value: float | str
    weights: LossWeights = LossWeights()
    addable: tuple[Col, ...] = ENRICHMENTS


def penalty_grid(
    parameters: Sequence[str] = ("ratio", "type_change", "remove"),
    factors: Sequence[float] = (0.25, 4.0),
    base: LossWeights = LossWeights(),
) -> list[AdjusterSetting]:
    """Settings for a one-at-a-time sweep: the defaults, additions switched off, and each
    LossWeights field in `parameters` scaled by each factor with the others at default.

    Raises:
        ValueError: For a name that is not a LossWeights field.
    """
    known = {f.name for f in fields(LossWeights)}
    unknown = set(parameters) - known
    if unknown:
        raise ValueError(f"not LossWeights fields: {sorted(unknown)}")
    settings = [AdjusterSetting(DEFAULT, "", base), AdjusterSetting(ADDABLE, "none", base, ())]
    for name in parameters:
        for factor in factors:
            value = getattr(base, name) * factor
            settings.append(AdjusterSetting(name, value, replace(base, **{name: value})))
    return settings


def success_column(target: Style | str) -> str:
    """Column of the sensitivity frames holding adjustment success toward `target`."""
    return f"{SUCCESS}_{target}"


def _summarize_evaluation(evaluation: pd.DataFrame, judges: Sequence[str]) -> dict[str, float]:
    """Success per target, mean judge agreement over targets and judges, and mean change counts."""
    return {
        **{success_column(t): float(v) for t, v in evaluation[SUCCESS].items()},
        JUDGE_MEAN: float(evaluation[[judge_column(j) for j in judges]].to_numpy().mean()),
        **evaluation[list(CHANGE_COUNTS)].mean().to_dict(),
    }


def addition_gains(
    recipes: pd.DataFrame,
    space: SearchSpace,
    targets: Sequence[Style | str],
    weights: LossWeights = LossWeights(),
) -> pd.DataFrame:
    """Net gain in the adjuster's loss from adding each optional ingredient, before its
    fixed add cost, for real recipes of other styles that lack it.

    The gain is (best loss without the ingredient) - (best loss with it, add cost set to 0).
    The ingredient is added exactly when this exceeds `weights.add`. GAIN_SPREAD (max - min
    over recipes) should be zero, confirming the gain does not depend on the recipe.

    Returns:
        One row per (TARGET, INGREDIENT) with N_LACKING, NET_GAIN (the mean) and GAIN_SPREAD.
    """
    free = replace(weights, add=0.0)
    style = recipes[Col.style]
    rows = []
    for t in targets:
        for ingredient in OPTIONAL:
            lacking = recipes[(style != t) & (recipes[ingredient] == 0)]
            others = tuple(c for c in ENRICHMENTS if c != ingredient)
            _, without = adjust_many(lacking, t, space, free, addable=others)
            _, with_it = adjust_many(lacking, t, space, free, addable=(*others, ingredient))
            gain = without["loss_total"] - with_it["loss_total"]
            rows.append({
                TARGET: str(t), INGREDIENT: str(ingredient), N_LACKING: len(lacking),
                NET_GAIN: float(gain.mean()), GAIN_SPREAD: float(gain.max() - gain.min()),
            })
    return pd.DataFrame(rows).set_index([TARGET, INGREDIENT])


def penalty_sensitivity(
    recipes: pd.DataFrame,
    space: SearchSpace,
    targets: Sequence[Style | str],
    settings: Sequence[AdjusterSetting] | None = None,
    *,
    judges: Sequence[str] = JUDGES,
    config: CVConfig = CVConfig(),
) -> pd.DataFrame:
    """Adjustment results under each setting (default: `penalty_grid()`).

    Returns:
        One row per setting, indexed by (PARAMETER, VALUE): `success_column(t)` for each
        target, JUDGE_MEAN (share labelled the target by the out-of-fold judges, averaged
        over targets and judges), and the mean of each CHANGE_COUNTS over targets.
    """
    rows = {}
    for s in settings if settings is not None else penalty_grid():
        evaluation = evaluate_adjustments(
            recipes, space, targets, weights=s.weights, addable=s.addable, judges=judges, config=config, n_boot=1
        )
        rows[(s.parameter, s.value)] = _summarize_evaluation(evaluation, judges)
    logger.debug("penalty sensitivity over {} settings", len(rows))
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis([PARAMETER, VALUE])


def type_weight_sensitivity(
    recipes: pd.DataFrame,
    targets: Sequence[Style | str],
    values: Sequence[float] = (0.5, 1.0, 2.0),
    *,
    models: Sequence[str] = WEIGHT_SENSITIVE_MODELS,
    judges: Sequence[str] = JUDGES,
    addable: Collection[Col] = ENRICHMENTS,
    config: CVConfig = CVConfig(),
) -> pd.DataFrame:
    """Classifier accuracy and adjustment results as the type-column weight varies.

    For each weight: repeated-CV accuracy of each model in `models` built with that weight,
    and the adjuster run on centroids fit with that weight. The judges keep the default
    weight, so they stay a fixed, independent reference.

    Returns:
        One row per TYPE_WEIGHT. Columns are (ACCURACY, model) and (ACCURACY_SD, model) for
        each model, then the adjustment summary columns of `penalty_sensitivity`.
    """
    X, y = recipes[FEATURES], recipes[Col.style]
    rows = {}
    for w in values:
        folds = cross_validate(make_models(include=models, type_weight=w), X, y, make_cv(config)).folds
        per_repeat = repeat_means(folds, (ACCURACY,)).groupby("model")[ACCURACY]
        pipe = fit_centroids(X, y, type_weight=w)
        evaluation = evaluate_adjustments(
            recipes, build_search_space(pipe, recipes), targets, addable=addable, judges=judges, config=config, n_boot=1
        )
        rows[w] = {
            **{(ACCURACY, m): float(v) for m, v in per_repeat.mean().items()},
            **{(ACCURACY_SD, m): float(v) for m, v in per_repeat.std().items()},
            **{("adjustment", k): v for k, v in _summarize_evaluation(evaluation, judges).items()},
        }
    logger.debug("type-weight sensitivity over {}", list(values))
    frame = pd.DataFrame.from_dict(rows, orient="index").rename_axis(TYPE_WEIGHT)
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)
    return frame

