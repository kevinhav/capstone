"""State and display helpers shared by the app's pages."""

from dataclasses import dataclass
from typing import Final

import pandas as pd
import streamlit as st
from sklearn.pipeline import Pipeline

from capstone.config import INGREDIENT_ORDER, label  # noqa: F401  (re-exported for the views)
from capstone.data import load_provenance, load_recipes
from capstone.features import numeric_bounds
from capstone.models import SearchSpace, build_search_space, load_or_fit_centroids
from capstone.utilities import setup_logging

BASE_RECIPE_KEY: Final = "base_recipe"  # session key: recipe the Formulation page starts from
DEFAULT_RECIPE: Final = "new_york_001"


@dataclass(frozen=True, eq=False)
class AppModel:
    recipes: pd.DataFrame
    provenance: pd.DataFrame
    pipe: Pipeline
    space: SearchSpace
    low: pd.Series  # smallest amount of each ingredient in the curated recipes (fat/sugar: when used)
    high: pd.Series


@st.cache_resource
def load_model() -> AppModel:
    """Curated recipes and the fitted centroid model, loaded once per server."""
    setup_logging()
    recipes = load_recipes()
    pipe = load_or_fit_centroids(recipes)
    low, high = numeric_bounds(recipes)
    return AppModel(recipes, load_provenance(), pipe, build_search_space(pipe, recipes), low, high)
