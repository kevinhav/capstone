import pandas as pd
import pytest

from capstone.config import CATEGORICAL, FEATURES, NUMERIC, STYLES, Col, FrankensteinConfig, LossWeights
from capstone.data import Recipe, load_recipes, make_frankensteins, to_grams
from capstone.models import adjust, adjust_many, build_search_space, fit_centroids, predict, resolve_target


@pytest.fixture(scope="module")
def recipes() -> pd.DataFrame:
    return load_recipes()


@pytest.fixture(scope="module")
def pipe(recipes):
    return fit_centroids(recipes, recipes[Col.style])


@pytest.fixture(scope="module")
def space(pipe, recipes):
    return build_search_space(pipe, recipes)


def test_recipes_load_complete(recipes):
    assert set(recipes[Col.style]) == set(STYLES)
    assert recipes[FEATURES].notna().all().all()
    assert (recipes[NUMERIC] >= 0).all().all()


def test_recipe_round_trip(recipes):
    row = recipes.iloc[0]
    pd.testing.assert_series_equal(Recipe.from_row(row).to_row(), row[FEATURES].rename(row.name), check_dtype=False)


def test_recipe_absent_optional_is_consistent():
    r = Recipe(flour_type="bread", water=65, salt=2, yeast=0.5, yeast_type="instant", fat=3.0, fat_type="none")
    assert r.fat == 0 and r.fat_type == "none"


def test_to_grams_requires_density_for_volume():
    assert to_grams(1, "oz") == pytest.approx(28.3495)
    with pytest.raises(ValueError):
        to_grams(1, "cup")


def test_resolve_target_normalizes(pipe):
    styles = list(pipe.classes_)
    assert resolve_target({"neapolitan": 30, "new-york": 70}, styles) == resolve_target({"neapolitan": 0.3, "new-york": 0.7}, styles)
    with pytest.raises(ValueError):
        resolve_target({"detroit": 1}, styles)
    with pytest.raises(ValueError):
        resolve_target({"neapolitan": 0}, styles)


def test_default_weights_never_add_ingredients(recipes, space):
    frank = make_frankensteins(recipes, FrankensteinConfig(n=40, seed=1))
    for style in STYLES:
        adjusted, info = adjust_many(frank, style, space)
        assert info["n_added"].sum() == 0
        assert ((frank[Col.fat] == 0) <= (adjusted[Col.fat] == 0)).all()


def test_adjustment_moves_toward_target(recipes, pipe, space):
    recipe = recipes.loc["new_york_001"]
    result = adjust(recipe, "neapolitan", space)
    assert predict(pipe, result.recipe.to_frame().T).iloc[0] == "neapolitan"
    assert set(result.recipe.index) == set(FEATURES)
    assert result.recipe[CATEGORICAL].isin(recipes[CATEGORICAL].stack().unique()).all()


def test_cheap_additions_allow_adding(recipes, space):
    frank = make_frankensteins(recipes, FrankensteinConfig(n=40, seed=1))
    _, info = adjust_many(frank, "sicilian", space, LossWeights(add=0.0))
    assert info["n_added"].sum() > 0
