import math

import pandas as pd
import pytest

from capstone.config import CATEGORICAL, FEATURES, NUMERIC, STYLES, Col, FrankensteinConfig, LossWeights
from capstone.data import (
    Recipe,
    dough_ball_grams,
    load_recipes,
    make_frankensteins,
    scale_recipe,
    to_baker_percentage,
    to_grams,
)
from capstone.models import adjust, adjust_many, build_search_space, evaluate_adjustments, fit_centroids, predict, resolve_target


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


def test_scale_recipe_inverts_baker_percentage(recipes):
    recipe = recipes.loc["new_york_001"]
    grams = scale_recipe(recipe, 1000)
    assert grams.sum() == pytest.approx(1000)
    for c in NUMERIC:
        assert to_baker_percentage(grams[c], grams[Col.flour]) == pytest.approx(recipe[c])


def test_dough_ball_grams_from_thickness_factor():
    # 14-inch round: pi * 7^2 = 153.94 sq in; at 0.085 oz/sq in that's 13.08 oz
    assert dough_ball_grams(0.085, math.pi * 7**2) == pytest.approx(370.9, abs=0.1)


def test_resolve_target_normalizes(pipe):
    styles = list(pipe.classes_)
    assert resolve_target({"neapolitan": 30, "new-york": 70}, styles) == resolve_target({"neapolitan": 0.3, "new-york": 0.7}, styles)
    with pytest.raises(ValueError):
        resolve_target({"detroit": 1}, styles)
    with pytest.raises(ValueError):
        resolve_target({"neapolitan": 0}, styles)


def test_disallowed_additions_never_happen(recipes, space):
    frank = make_frankensteins(recipes, FrankensteinConfig(n=40, seed=1))
    for style in STYLES:
        adjusted, info = adjust_many(frank, style, space, addable=())
        assert info["n_added"].sum() == 0
        assert ((frank[Col.fat] == 0) <= (adjusted[Col.fat] == 0)).all()
    adjusted, _ = adjust_many(frank, "new-york", space, addable=[Col.sugar])
    assert ((frank[Col.fat] == 0) <= (adjusted[Col.fat] == 0)).all()  # fat stays out, sugar may come in


def test_default_weights_add_enrichments_within_observed_range(recipes, space):
    lean = recipes[(recipes[Col.fat] == 0) & (recipes[Col.style] != "new-york")]
    adjusted, info = adjust_many(lean, "new-york", space)
    assert info["n_added"].sum() > 0
    added = adjusted.loc[adjusted[Col.fat] > 0, Col.fat]
    used = recipes.loc[recipes[Col.fat] > 0, Col.fat]
    assert added.between(used.min(), used.max()).all()


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


def test_range_warning_flags_only_unusual_amounts(recipes):
    from types import SimpleNamespace

    from capstone.app.views.formulation import range_warning
    from capstone.features import numeric_bounds

    low, high = numeric_bounds(recipes)
    model = SimpleNamespace(low=low, high=high)
    assert range_warning(model, Col.water, float(recipes[Col.water].median())) == ""
    assert range_warning(model, Col.water, high[Col.water] + 1).startswith("Higher")
    assert range_warning(model, Col.salt, low[Col.salt] / 2).startswith("Lower")
    assert range_warning(model, Col.fat, 0.0) == ""  # leaving out fat is never unusual


def test_unchanged_types_are_not_reported_as_changes():
    from capstone.app.views.formulation import _change

    assert _change(Col.flour_type, "double_zero", "double_zero") == ""
    assert _change(Col.flour_type, "high-gluten", "double_zero") == "swapped"
    assert _change(Col.sugar_type, "none", "white") == "added"
    assert _change(Col.fat_type, "lard", "none") == "removed"


def test_type_changes_are_real(recipes, space):
    for style in STYLES:
        adjusted, info = adjust_many(recipes, style, space)
        changed = (adjusted[CATEGORICAL].astype(str) != recipes[CATEGORICAL].astype(str)).sum(axis=1)
        assert (info["n_type_changes"] <= changed).all()


def test_unknown_type_is_imputed_from_training_shares():
    from capstone.config import ABSENT, UNKNOWN
    from capstone.features import ImputingOneHotEncoder

    train = pd.DataFrame({"t": ["a", "a", "b", ABSENT, UNKNOWN]})
    enc = ImputingOneHotEncoder().fit(train)
    assert list(enc.get_feature_names_out()) == ["t_a", "t_b", f"t_{ABSENT}"]  # unknown is never a level
    out = enc.transform(pd.DataFrame({"t": ["b", UNKNOWN, "unseen"]}))
    assert out[0].tolist() == [0.0, 1.0, 0.0]
    assert out[1].tolist() == pytest.approx([2 / 3, 1 / 3, 0.0])  # shares among present types
    assert out[2].tolist() == [0.0, 0.0, 0.0]


def test_naming_an_unknown_type_is_not_a_swap(recipes, space):
    from capstone.app.views.formulation import _change
    from capstone.config import ABSENT, UNKNOWN

    unknown = recipes[(recipes[CATEGORICAL] == UNKNOWN).any(axis=1)]
    assert len(unknown) > 0
    adjusted, info = adjust_many(unknown, STYLES[0], space)
    assert not (adjusted[CATEGORICAL] == UNKNOWN).any().any()
    before, after = unknown[CATEGORICAL].astype(str), adjusted[CATEGORICAL].astype(str)
    # a swap: a stated type changed to another type (to or from ABSENT is an add/remove instead)
    known = (before != UNKNOWN) & (before != after) & (before != ABSENT) & (after != ABSENT)
    assert (info["n_type_changes"] == known.sum(axis=1)).all()
    assert _change(Col.flour_type, UNKNOWN, "bread") == "specified"


def test_adjustment_evaluation_on_real_recipes(recipes, space):
    from capstone.models.evaluate import N_RECIPES, SUCCESS, SUCCESS_HI, SUCCESS_LO, TARGET_BEFORE, judge_column

    ev = evaluate_adjustments(recipes, space, STYLES, n_boot=50)
    assert list(ev.index) == [str(s) for s in STYLES]
    assert (ev[N_RECIPES] == [int((recipes[Col.style] != s).sum()) for s in STYLES]).all()
    assert ((ev[SUCCESS_LO] <= ev[SUCCESS]) & (ev[SUCCESS] <= ev[SUCCESS_HI])).all()
    assert (ev[SUCCESS] >= ev[TARGET_BEFORE]).all()  # adjusting never moves recipes away on balance
    assert ev[judge_column("random forest")].between(0, 1).all()
