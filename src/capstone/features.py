"""Feature-space representation of recipes: preprocessing, feature names, bounds, distances."""

from collections.abc import Sequence
from typing import Final

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from capstone.config import ABSENT, CATEGORICAL, NUMERIC, OPTIONAL, UNKNOWN, Col, label

NUM_BLOCK: Final = "num"
CAT_BLOCK: Final = "cat"
PREP_STEP: Final = "prep"


class ImputingOneHotEncoder(TransformerMixin, BaseEstimator):
    """One-hot encoder that imputes UNKNOWN types from the training data.

    Known types encode as a usual one-hot row. An UNKNOWN type encodes as the share of
    each type among training recipes that use the ingredient (ABSENT excluded, since an
    unknown type still means the ingredient is present): the categorical analogue of mean
    imputation. UNKNOWN never becomes a level of its own, so it carries no style signal
    and is never a type the adjuster can choose. Types unseen in training encode as zeros.
    """

    def fit(self, X: pd.DataFrame, y: object = None) -> "ImputingOneHotEncoder":
        X = pd.DataFrame(X)
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]
        self.categories_ = [np.array(sorted(set(X[c]) - {UNKNOWN}), dtype=object) for c in X]
        self.shares_ = [
            X[c][~X[c].isin([UNKNOWN, ABSENT])].value_counts(normalize=True).reindex(levels, fill_value=0.0).to_numpy()
            for c, levels in zip(X, self.categories_)
        ]
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        X = pd.DataFrame(X, columns=self.feature_names_in_)
        blocks = []
        for c, levels, shares in zip(X, self.categories_, self.shares_):
            values = X[c].to_numpy(dtype=object)
            block = (values[:, None] == levels[None, :]).astype(float)
            block[values == UNKNOWN] = shares
            blocks.append(block)
        return np.hstack(blocks)

    def get_feature_names_out(self, input_features: Sequence[str] | None = None) -> np.ndarray:
        return np.array(
            [f"{c}_{k}" for c, levels in zip(self.feature_names_in_, self.categories_) for k in levels], dtype=object
        )


# We intentionally z-score because small changes in small ingredients have large impacts
# A percentage increase in salt/yeast matter far more than percentage increase in flour/water
def build_preprocessor(
    numeric: Sequence[Col] = NUMERIC,
    categorical: Sequence[Col] = CATEGORICAL,
    type_weight: float = 1.0,
) -> ColumnTransformer:
    """Z-score the numeric ratios and one-hot encode the ingredient types, imputing
    unstated (UNKNOWN) types from the training data (see `ImputingOneHotEncoder`).

    Args:
        numeric, categorical: Feature groups; either may be empty, for ablations.
        type_weight: Multiplier on the one-hot type columns, setting how much a type
            difference counts against a ratio difference in any distance (default 1).
    """
    blocks = []
    if numeric:
        blocks.append((NUM_BLOCK, StandardScaler(), [str(c) for c in numeric]))
    if categorical:
        blocks.append((CAT_BLOCK, ImputingOneHotEncoder(), [str(c) for c in categorical]))
    return ColumnTransformer(blocks, transformer_weights={CAT_BLOCK: type_weight} if categorical else None)


def feature_name(col: Col, category: str | None = None) -> str:
    """Name of a transformed column, e.g. 'num__water' or 'cat__flour_type_bread'."""
    if category is None:
        return f"{NUM_BLOCK}__{col}"
    return f"{CAT_BLOCK}__{col}_{category}"


def preprocessor(pipe: Pipeline) -> ColumnTransformer:
    """The fitted preprocessing step of a pipeline built on `build_preprocessor()`."""
    return pipe[PREP_STEP]


def feature_names(pipe: Pipeline) -> list[str]:
    """Transformed feature names of a fitted pipeline."""
    return list(preprocessor(pipe).get_feature_names_out())


def transform(pipe: Pipeline, X: pd.DataFrame) -> pd.DataFrame:
    """Recipes in the fitted pipeline's feature space, as a labeled frame."""
    prep = preprocessor(pipe)
    return pd.DataFrame(
        prep.transform(X[list(prep.feature_names_in_)]),
        index=X.index,
        columns=feature_names(pipe),
    )


def type_weight(pipe: Pipeline) -> float:
    """Multiplier the fitted pipeline applies to its one-hot type columns."""
    return float((preprocessor(pipe).transformer_weights or {}).get(CAT_BLOCK, 1.0))


def scaler_stats(pipe: Pipeline) -> tuple[np.ndarray, np.ndarray]:
    """(mean, scale) of the numeric StandardScaler, ordered as NUMERIC."""
    scaler = preprocessor(pipe).named_transformers_[NUM_BLOCK]
    return scaler.mean_, scaler.scale_


def category_levels(pipe: Pipeline) -> dict[Col, np.ndarray]:
    """Categories the one-hot encoder learned for each categorical column."""
    return dict(
        zip(CATEGORICAL, preprocessor(pipe).named_transformers_[CAT_BLOCK].categories_)
    )


def feature_labels(pipe: Pipeline) -> dict[str, str]:
    """Readable name for each transformed feature, e.g. 'num__water' -> 'Water' and
    'cat__flour_type_bread' -> 'Flour type: Bread'."""
    names = {feature_name(c): label(c) for c in NUMERIC}
    for col, levels in category_levels(pipe).items():
        names |= {feature_name(col, k): f"{label(col)}: {label(k)}" for k in levels}
    return names


def ratio_summary(pipe: Pipeline, reference: pd.DataFrame) -> pd.DataFrame:
    """Per numeric ratio: observed min and max over `reference`, and the fitted scaler's
    mean and population standard deviation (the mu_i and sigma_i used for z-scoring).

    Args:
        pipe: Fitted pipeline built on `build_preprocessor()`.
        reference: Recipes the scaler was fitted on.
    """
    mean, scale = scaler_stats(pipe)
    ratios = reference[NUMERIC]
    return pd.DataFrame(
        {"min": ratios.min().to_numpy(), "max": ratios.max().to_numpy(), "mean": mean, "std": scale},
        index=pd.Index(NUMERIC, name="ingredient"),
    )


def numeric_bounds(reference: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Observed (min, max) of each numeric ratio. Optional ingredients use only recipes
    that contain them, so the lower bound is the smallest amount actually used."""
    lo, hi = {}, {}
    for c in NUMERIC:
        values = reference[c][reference[c] > 0] if c in OPTIONAL else reference[c]
        lo[c], hi[c] = values.min(), values.max()
    return pd.Series(lo), pd.Series(hi)


# Optional approach instead of Euclidiean
# def gower_distance(frame: pd.DataFrame, numeric: Sequence[Col] = NUMERIC, categorical: Sequence[Col] = CATEGORICAL) -> pd.DataFrame:
#     """Pairwise Gower distance: range-normalized absolute difference for numeric
#     columns, 0/1 mismatch for categorical columns, averaged over all columns."""
#     parts = []
#     for c in numeric:
#         v = frame[c].to_numpy(dtype=float)
#         parts.append(np.abs(v[:, None] - v[None]) / (v.max() - v.min()))
#     for c in categorical:
#         v = frame[c].to_numpy(dtype=object)
#         parts.append((v[:, None] != v[None]).astype(float))
#     return pd.DataFrame(np.mean(parts, axis=0), index=frame.index, columns=frame.index)
