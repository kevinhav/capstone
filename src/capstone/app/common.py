"""State and display helpers shared by the app's pages."""

from dataclasses import dataclass
from typing import Final

import pandas as pd
import streamlit as st
from sklearn.pipeline import Pipeline

from capstone.config import Col
from capstone.data import load_provenance, load_recipes
from capstone.features import numeric_bounds
from capstone.models import SearchSpace, build_search_space, load_or_fit_centroids
from capstone.utilities import setup_logging

BASE_RECIPE_KEY: Final = "base_recipe"  # session key: recipe the Formulation page starts from
DEFAULT_RECIPE: Final = "new_york_001"

# each ingredient's amount followed by its type, so tables read one ingredient at a time
INGREDIENT_ORDER: Final[list[Col]] = [
    Col.flour_type, Col.water, Col.salt, Col.yeast, Col.yeast_type, Col.fat, Col.fat_type, Col.sugar, Col.sugar_type,
]

# plain-language names for enum values and columns
LABELS: Final[dict[str, str]] = {
    "neapolitan": "Neapolitan",
    "new-york": "New York",
    "sicilian": "Sicilian",
    "all-purpose": "All-purpose",
    "bread": "Bread",
    "high-gluten": "High-gluten",
    "double_zero": "Tipo 00",
    "semolina": "Semolina",
    "active-dry": "Active dry",
    "instant": "Instant",
    "fresh": "Fresh",
    "sourdough-starter": "Sourdough / poolish",
    "extra-virgin olive oil": "Olive oil",
    "butter": "Butter",
    "lard": "Lard",
    "vegetable oil": "Vegetable oil",
    "white": "White sugar",
    "brown": "Brown sugar",
    "honey": "Honey",
    "none": "None",
    Col.flour: "Flour",
    Col.water: "Water",
    Col.salt: "Salt",
    Col.yeast: "Yeast",
    Col.fat: "Fat",
    Col.sugar: "Sugar",
    Col.flour_type: "Flour type",
    Col.yeast_type: "Yeast type",
    Col.fat_type: "Fat type",
    Col.sugar_type: "Sugar type",
}


def label(value: object) -> str:
    """Display name for an enum value or column."""
    return LABELS.get(str(value), str(value))


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
