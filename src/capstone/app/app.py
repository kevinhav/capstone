import pandas as pd
import streamlit as st
from sklearn.pipeline import Pipeline

from capstone.app.plots import RadarSeries, triangle_radar
from capstone.config import FEATURES, NUMERIC, PLOT, STYLES, Col, FatType, FlourType, SugarType, YeastType
from capstone.data import Recipe, load_recipes
from capstone.models import SearchSpace, adjust, build_search_space, estimate_mix, load_or_fit_centroids, target_distance
from capstone.utilities import setup_logging

DEFAULT_RECIPE = "new_york_001"
CUSTOM = "(custom)"


@st.cache_resource
def load_model() -> tuple[pd.DataFrame, Pipeline, SearchSpace]:
    setup_logging()
    recipes = load_recipes()
    pipe = load_or_fit_centroids(recipes)
    return recipes, pipe, build_search_space(pipe, recipes)


def recipe_inputs(recipes: pd.DataFrame) -> Recipe:
    sample = st.selectbox("Start from", [CUSTOM] + list(recipes.index))
    base = Recipe.from_row(recipes.loc[DEFAULT_RECIPE if sample == CUSTOM else sample])

    def pick[E](label: str, enum: type[E], current: E) -> E:
        options = list(enum)
        return st.selectbox(label, options, index=options.index(current), key=f"{sample}-{label}")

    def amount(label: str, current: float, step: float) -> float:
        return st.number_input(f"{label} %", min_value=0.0, value=float(current), step=step, key=f"{sample}-{label}-amt")

    # Recipe treats a 0 amount or a "none" type as the ingredient being absent
    return Recipe(
        flour_type=pick("flour type", FlourType, base.flour_type),
        water=amount("water", base.water, 1.0),
        salt=amount("salt", base.salt, 0.1),
        yeast=amount("yeast", base.yeast, 0.05),
        yeast_type=pick("yeast type", YeastType, base.yeast_type),
        fat=amount("fat", base.fat, 0.5),
        fat_type=pick("fat type", FatType, base.fat_type),
        sugar=amount("sugar", base.sugar, 0.5),
        sugar_type=pick("sugar type", SugarType, base.sugar_type),
        recipe_id="original",
    )


def change_column(frame: pd.DataFrame) -> list[str]:
    before, after = frame.loc["original"], frame.loc["adjusted"]
    return [
        "" if before[c] == after[c] else (f"{after[c] - before[c]:+.2f}" if c in NUMERIC else "swapped")
        for c in FEATURES
    ]


def main() -> None:
    st.set_page_config(page_title="Pizza dough adjuster", layout="wide")
    st.title("Pizza dough adjuster")
    recipes, pipe, space = load_model()

    with st.sidebar:
        st.header("Your recipe (baker's %, flour = 100)")
        recipe = recipe_inputs(recipes).to_row()
        st.header("Target style mix")
        shares = {s: st.slider(s, 0, 100, 100 if s == STYLES[0] else 0, 5) for s in STYLES}

    if sum(shares.values()) == 0:
        st.info("Set at least one target style above 0%.")
        return

    result = adjust(recipe, shares, space)
    frame = pd.DataFrame([recipe, result.recipe.rename("adjusted")])
    mixes = estimate_mix(pipe, frame)
    dist = target_distance(pipe, frame, shares)
    total = sum(shares.values())

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Style mix")
        st.pyplot(triangle_radar(STYLES, {
            "original": RadarSeries(mixes.loc["original", STYLES], PLOT.original_color),
            "adjusted": RadarSeries(mixes.loc["adjusted", STYLES], PLOT.adjusted_color),
            "target": RadarSeries([shares[s] / total for s in STYLES], PLOT.target_color, filled=False),
        }))
    with right:
        st.subheader("Adjusted recipe")
        table = frame.T.assign(change=change_column(frame))
        for col in ("original", "adjusted"):
            table[col] = [f"{v:.2f}" if c in NUMERIC else v for c, v in zip(FEATURES, table[col])]
        st.dataframe(table, width="stretch")
        st.caption(
            f"{result.n_type_changes} type swap(s), {result.n_removed} ingredient(s) removed, "
            f"{result.n_added} added. Distance to target: {dist['original']:.2f} -> {dist['adjusted']:.2f}"
        )


main()
