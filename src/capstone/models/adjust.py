"""Minimal-change adjustment of a recipe toward a style, or a blend of styles.

For a recipe x and target centroid c (a single style or a share-weighted blend),
minimizes

    L(x') = w_target * ||phi(x') - c||^2          (pull toward the target)
          + w_ratio  * sum_j (z'_j - z_j)^2        (changed ratios, lenient)
          + w_type   * #(ingredient types swapped) (moderate)
          + w_remove * #(optional ingredients dropped)
          + w_add    * #(optional ingredients added) (very strict)

where phi is the centroid pipeline's preprocessing (z-scored ratios + one-hot types).
Types are discrete, so every combination of (flour, yeast, fat, sugar) type is
enumerated; for a fixed combination the ratio part is a separable box-constrained
quadratic whose solution is the unconstrained optimum clipped to the observed range
of each ingredient, so the search is exact.
"""

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.pipeline import Pipeline

from capstone.config import ABSENT, CATEGORICAL, FEATURES, NUMERIC, OPTIONAL, Col, LossWeights, Target
from capstone.features import category_levels, feature_name, numeric_bounds, scaler_stats
from capstone.models.centroids import blend_centroid, resolve_target, styles


@dataclass(frozen=True, eq=False)
class SearchSpace:
    """Everything about the feature space the adjuster needs, computed once per fitted pipeline."""

    pipe: Pipeline
    levels: dict[Col, np.ndarray]
    combos: np.ndarray  # (n_combos, len(CATEGORICAL)) every type combination
    present: dict[Col, np.ndarray]  # optional ingredient -> is it present in each combo
    mean: np.ndarray
    scale: np.ndarray
    lo_z: np.ndarray
    hi_z: np.ndarray
    zero_z: np.ndarray


@dataclass(frozen=True)
class LossBreakdown:
    target: float
    ratio: float
    type: float
    remove: float
    add: float

    @property
    def total(self) -> float:
        return self.target + self.ratio + self.type + self.remove + self.add


@dataclass(frozen=True)
class Adjustment:
    """Result of adjusting one recipe."""

    recipe: pd.Series
    target: dict[str, float]
    loss: LossBreakdown
    n_type_changes: int
    n_added: int
    n_removed: int


def build_search_space(pipe: Pipeline, reference: pd.DataFrame) -> SearchSpace:
    """Precompute type combinations, scaler stats, and z-scaled ratio bounds.

    Args:
        pipe: Fitted centroid pipeline (see `fit_centroids`).
        reference: Real recipes whose observed ranges bound the adjusted ratios.
    """
    levels = category_levels(pipe)
    combos = np.array(list(product(*(levels[c] for c in CATEGORICAL))), dtype=object)
    present = {r: combos[:, CATEGORICAL.index(t)] != ABSENT for r, t in OPTIONAL.items()}
    mean, scale = scaler_stats(pipe)
    lo, hi = numeric_bounds(reference)
    logger.debug("search space: {} type combinations", len(combos))
    return SearchSpace(
        pipe=pipe, levels=levels, combos=combos, present=present, mean=mean, scale=scale,
        lo_z=(lo[NUMERIC].to_numpy() - mean) / scale,
        hi_z=(hi[NUMERIC].to_numpy() - mean) / scale,
        zero_z=(0.0 - mean) / scale,
    )


def _cat_distance(space: SearchSpace, centroid: pd.Series) -> np.ndarray:
    """Squared distance of each type combination's one-hot encoding to the centroid."""
    total = np.zeros(len(space.combos))
    for j, col in enumerate(CATEGORICAL):
        p = np.array([centroid[feature_name(col, k)] for k in space.levels[col]])
        lookup = dict(zip(space.levels[col], p))
        pv = np.array([lookup[v] for v in space.combos[:, j]])
        total += (p**2).sum() + 1 - 2 * pv
    return total


def _adjust_one(
    recipe: pd.Series, centroid: pd.Series, cat_dist: np.ndarray, target: dict[str, float],
    space: SearchSpace, w: LossWeights,
) -> Adjustment:
    c_num = centroid[[feature_name(c) for c in NUMERIC]].to_numpy(dtype=float)
    z0 = (recipe[NUMERIC].to_numpy(dtype=float) - space.mean) / space.scale
    orig_types = recipe[CATEGORICAL].to_numpy(dtype=object)
    orig_present = {r: recipe[r] > 0 for r in OPTIONAL}
    n_combos = len(space.combos)

    keep = np.clip((w.target * c_num + w.ratio * z0) / (w.target + w.ratio), space.lo_z, space.hi_z)
    added = np.clip(c_num, space.lo_z, space.hi_z)

    z = np.tile(keep, (n_combos, 1))
    counted = np.ones((n_combos, len(NUMERIC)), dtype=bool)  # dims whose ratio change is penalized
    n_add, n_remove = np.zeros(n_combos), np.zeros(n_combos)
    for r in OPTIONAL:
        j = NUMERIC.index(r)
        here = space.present[r]
        z[~here, j] = space.zero_z[j]
        counted[~here, j] = False
        if orig_present[r]:
            n_remove += ~here
        else:
            z[here, j], counted[here, j] = added[j], False
            n_add += here

    n_type = np.zeros(n_combos)
    for j, col in enumerate(CATEGORICAL):
        changed = space.combos[:, j] != orig_types[j]
        ratio = next((r for r, t in OPTIONAL.items() if t == col), None)
        if ratio is not None:
            changed &= space.present[ratio] & orig_present[ratio]  # add/remove are counted separately
        n_type += changed

    components = {
        "target": w.target * (((z - c_num) ** 2).sum(axis=1) + cat_dist),
        "ratio": w.ratio * (((z - z0) ** 2) * counted).sum(axis=1),
        "type": w.type_change * n_type,
        "remove": w.remove * n_remove,
        "add": w.add * n_add,
    }
    best = int(np.argmin(sum(components.values())))

    adjusted = recipe[FEATURES].copy()
    adjusted[NUMERIC] = z[best] * space.scale + space.mean
    adjusted[CATEGORICAL] = space.combos[best]
    for r in OPTIONAL:
        if not space.present[r][best]:
            adjusted[r] = 0.0
    return Adjustment(
        recipe=adjusted,
        target=target,
        loss=LossBreakdown(**{k: float(v[best]) for k, v in components.items()}),
        n_type_changes=int(n_type[best]),
        n_added=int(n_add[best]),
        n_removed=int(n_remove[best]),
    )


def adjust(recipe: pd.Series, target: Target, space: SearchSpace, weights: LossWeights = LossWeights()) -> Adjustment:
    """Adjust one recipe toward a style or style mix with minimal change.

    Args:
        recipe: Row with the FEATURES columns (e.g. from `load_recipes()` or `Recipe.to_row()`).
        target: A style name, or {style: share} (shares are normalized).
        space: From `build_search_space`.
        weights: Strictness of each kind of change.
    """
    mix = resolve_target(target, styles(space.pipe))
    centroid = blend_centroid(space.pipe, mix)
    return _adjust_one(recipe, centroid, _cat_distance(space, centroid), mix, space, weights)


def adjust_many(
    recipes: pd.DataFrame, target: Target, space: SearchSpace, weights: LossWeights = LossWeights()
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Adjust every recipe toward `target`.

    Returns:
        (adjusted recipes, per-recipe loss breakdown and change counts), both indexed like `recipes`.
    """
    mix = resolve_target(target, styles(space.pipe))
    centroid = blend_centroid(space.pipe, mix)
    cat_dist = _cat_distance(space, centroid)
    adjusted, info = [], []
    for rid, recipe in recipes.iterrows():
        a = _adjust_one(recipe, centroid, cat_dist, mix, space, weights)
        adjusted.append(a.recipe.rename(rid))
        info.append({
            "recipe_id": rid,
            **{f"loss_{k}": v for k, v in vars(a.loss).items()},
            "loss_total": a.loss.total,
            "n_type_changes": a.n_type_changes, "n_added": a.n_added, "n_removed": a.n_removed,
        })
    logger.debug("adjusted {} recipes toward {}", len(recipes), mix)
    return pd.DataFrame(adjusted), pd.DataFrame(info).set_index("recipe_id")
