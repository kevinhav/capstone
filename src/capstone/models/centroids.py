"""Style centroids in the preprocessed feature space, affinity scores, and style mixes."""

from typing import Final

import numpy as np
import pandas as pd
from loguru import logger
from scipy.optimize import nnls
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import pairwise_distances
from sklearn.neighbors import NearestCentroid
from sklearn.pipeline import Pipeline

from capstone.config import ARTIFACTS, CATEGORICAL, FEATURES, NUMERIC, Col, Target
from capstone.features import PREP_STEP, build_preprocessor, feature_names, transform
from capstone.utilities import frame_hash, load_model, save_model

CENTROID_STEP: Final = "centroid"
_SUM_TO_ONE_PENALTY: Final = 1e3  # weight of the soft sum-to-one row in estimate_mix


def fit_centroids(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Fit preprocessing + NearestCentroid, giving one centroid per style.

    Args:
        X: Recipes with the FEATURES columns.
        y: Style label per recipe.
    """
    pipe = Pipeline([(PREP_STEP, build_preprocessor()), (CENTROID_STEP, NearestCentroid())])
    return pipe.fit(X[FEATURES], y)


def load_or_fit_centroids(recipes: pd.DataFrame) -> Pipeline:
    """The cached centroid pipeline for these recipes, fitting and caching it if missing or stale."""
    key = frame_hash(recipes[FEATURES + [Col.style]])
    pipe = load_model(ARTIFACTS.style_centroids, key)
    if pipe is None:
        pipe = fit_centroids(recipes, recipes[Col.style])
        save_model(pipe, ARTIFACTS.style_centroids, key)
    return pipe


def styles(pipe: Pipeline) -> list[str]:
    """Style labels in the order the centroids are stored."""
    return list(pipe[CENTROID_STEP].classes_)


def centroids(pipe: Pipeline) -> pd.DataFrame:
    """Centroid coordinates, one row per style, in the transformed feature space.
    Categorical coordinates are the share of that style's recipes using each category."""
    return pd.DataFrame(pipe[CENTROID_STEP].centroids_, index=styles(pipe), columns=feature_names(pipe))


def distances(pipe: Pipeline, X: pd.DataFrame) -> pd.DataFrame:
    """Euclidean distance from each recipe to each style centroid."""
    return pd.DataFrame(pairwise_distances(transform(pipe, X), centroids(pipe)), index=X.index, columns=styles(pipe))


def affinity(pipe: Pipeline, X: pd.DataFrame) -> pd.DataFrame:
    """Softmax over negative centroid distance. A similarity score, not a calibrated probability."""
    w = np.exp(-distances(pipe, X))
    return w.div(w.sum(axis=1), axis=0)


def predict(pipe: Pipeline, X: pd.DataFrame) -> pd.Series:
    """Nearest-centroid style for each recipe."""
    return pd.Series(pipe.predict(X[FEATURES]), index=X.index)


def resolve_target(target: Target, known: list[str]) -> dict[str, float]:
    """Normalize a style name or {style: share} mix to shares summing to 1.

    {"neapolitan": 30, "new-york": 70} and {"neapolitan": .3, "new-york": .7} are the
    same request; zero shares are dropped.

    Raises:
        ValueError: For unknown styles, negative shares, or all-zero shares.
    """
    mix = {str(target): 1.0} if isinstance(target, str) else {str(k): float(v) for k, v in target.items()}
    unknown = set(mix) - set(known)
    if unknown:
        raise ValueError(f"unknown styles: {sorted(unknown)}")
    if any(v < 0 for v in mix.values()) or sum(mix.values()) <= 0:
        raise ValueError("style shares must be non-negative and not all zero")
    total = sum(mix.values())
    return {k: v / total for k, v in sorted(mix.items()) if v > 0}


def blend_centroid(pipe: Pipeline, target: Target) -> pd.Series:
    """Share-weighted average of the style centroids for a style or style mix."""
    cents = centroids(pipe)
    return sum(share * cents.loc[style] for style, share in resolve_target(target, styles(pipe)).items())


def target_distance(pipe: Pipeline, X: pd.DataFrame, target: Target) -> pd.Series:
    """Euclidean distance of each recipe to the (blended) target centroid."""
    c = blend_centroid(pipe, target).to_numpy()
    return pd.Series(np.linalg.norm(transform(pipe, X).to_numpy() - c, axis=1), index=X.index)


def estimate_mix(pipe: Pipeline, X: pd.DataFrame) -> pd.DataFrame:
    """Style mix that best reconstructs each recipe from the centroids: non-negative,
    sum-to-one least-squares weights minimizing ||phi(x) - sum_s w_s c_s||. A coarse
    descriptor, since centroids are not well separated in every direction."""
    C = centroids(pipe).to_numpy().T
    A = np.vstack([C, _SUM_TO_ONE_PENALTY * np.ones(C.shape[1])])
    mix = np.array([nnls(A, np.append(z, _SUM_TO_ONE_PENALTY))[0] for z in transform(pipe, X).to_numpy()])
    return pd.DataFrame(mix / mix.sum(axis=1, keepdims=True), index=X.index, columns=styles(pipe))


def centroid_profile(recipes: pd.DataFrame, pipe: Pipeline) -> dict[str, dict[str, object]]:
    """Human-readable summary per style: recipe count, numeric means in baker's %,
    category shares, and the transformed-space centroid."""
    cents = centroids(pipe)
    profile = {}
    for style, group in recipes.groupby(Col.style.value):
        profile[style] = {
            "n_recipes": len(group),
            "numeric_mean": group[NUMERIC].mean().round(4).to_dict(),
            "category_share": {str(c): group[c].value_counts(normalize=True).round(4).to_dict() for c in CATEGORICAL},
            "centroid": cents.loc[style].round(6).to_dict(),
        }
    logger.debug("built centroid profile for {} styles", len(profile))
    return profile


class AffinityClassifier(BaseEstimator, ClassifierMixin):
    """Nearest-centroid classifier with softmax-over-negative-distance affinity scores.

    Operates on already-preprocessed features, so it composes in a Pipeline after
    `build_preprocessor()` and can be cross-validated like any sklearn estimator.
    """

    def fit(self, X: np.ndarray, y: np.ndarray) -> "AffinityClassifier":
        self.centroid_ = NearestCentroid().fit(X, y)
        self.classes_ = self.centroid_.classes_
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        w = np.exp(-pairwise_distances(X, self.centroid_.centroids_))
        return w / w.sum(axis=1, keepdims=True)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.classes_[self.predict_proba(X).argmax(axis=1)]
