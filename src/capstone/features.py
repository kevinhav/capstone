"""Feature-space representation of recipes: preprocessing, feature names, bounds, distances."""

from collections.abc import Sequence
from typing import Final

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from capstone.config import CATEGORICAL, NUMERIC, OPTIONAL, Col

NUM_BLOCK: Final = "num"
CAT_BLOCK: Final = "cat"
PREP_STEP: Final = "prep"


def build_preprocessor(numeric: Sequence[Col] = NUMERIC, categorical: Sequence[Col] = CATEGORICAL) -> ColumnTransformer:
    """Z-score the numeric ratios and one-hot encode the ingredient types.

    Either group may be empty, which makes the transformer reusable for ablations.
    """
    blocks = []
    if numeric:
        blocks.append((NUM_BLOCK, StandardScaler(), [str(c) for c in numeric]))
    if categorical:
        blocks.append((CAT_BLOCK, OneHotEncoder(handle_unknown="ignore", sparse_output=False), [str(c) for c in categorical]))
    return ColumnTransformer(blocks)


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
    return pd.DataFrame(prep.transform(X[list(prep.feature_names_in_)]), index=X.index, columns=feature_names(pipe))


def scaler_stats(pipe: Pipeline) -> tuple[np.ndarray, np.ndarray]:
    """(mean, scale) of the numeric StandardScaler, ordered as NUMERIC."""
    scaler = preprocessor(pipe).named_transformers_[NUM_BLOCK]
    return scaler.mean_, scaler.scale_


def category_levels(pipe: Pipeline) -> dict[Col, np.ndarray]:
    """Categories the one-hot encoder learned for each categorical column."""
    return dict(zip(CATEGORICAL, preprocessor(pipe).named_transformers_[CAT_BLOCK].categories_))


def numeric_bounds(reference: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Observed (min, max) of each numeric ratio. Optional ingredients use only recipes
    that contain them, so the lower bound is the smallest amount actually used."""
    lo, hi = {}, {}
    for c in NUMERIC:
        values = reference[c][reference[c] > 0] if c in OPTIONAL else reference[c]
        lo[c], hi[c] = values.min(), values.max()
    return pd.Series(lo), pd.Series(hi)


def gower_distance(frame: pd.DataFrame, numeric: Sequence[Col] = NUMERIC, categorical: Sequence[Col] = CATEGORICAL) -> pd.DataFrame:
    """Pairwise Gower distance: range-normalized absolute difference for numeric
    columns, 0/1 mismatch for categorical columns, averaged over all columns."""
    parts = []
    for c in numeric:
        v = frame[c].to_numpy(dtype=float)
        parts.append(np.abs(v[:, None] - v[None]) / (v.max() - v.min()))
    for c in categorical:
        v = frame[c].to_numpy(dtype=object)
        parts.append((v[:, None] != v[None]).astype(float))
    return pd.DataFrame(np.mean(parts, axis=0), index=frame.index, columns=frame.index)
