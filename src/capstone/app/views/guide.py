"""'How does this work?': the recipe format, centroids, affinity, and adjustment in plain language."""

import pandas as pd
import streamlit as st

from capstone.app.common import INGREDIENT_ORDER, AppModel, label, load_model
from capstone.config import NUMERIC, STYLES, Col
from capstone.models import centroid_profile


def _style_averages(model: AppModel) -> pd.DataFrame:
    """One row per style: recipe count, average amounts, and the most common type of each ingredient."""
    profile = centroid_profile(model.recipes, model.pipe)
    rows = {}
    for style in STYLES:
        p = profile[style]
        cells = {
            c: p["numeric_mean"][c] if c in NUMERIC else label(max(p["category_share"][c], key=p["category_share"][c].get))
            for c in INGREDIENT_ORDER
        }
        rows[label(style)] = {"Recipes": p["n_recipes"], **{label(c): v for c, v in cells.items()}}
    return pd.DataFrame(rows).T


def render() -> None:
    model = load_model()
    n = len(model.recipes)
    st.title("How does this work?")
    st.markdown(
        f"This app compares a pizza dough recipe with **{n} curated recipes** from three styles "
        "(Neapolitan, New York and Sicilian). It tells you which style your dough is closest to, "
        "and suggests the smallest changes that would move it toward a style you choose."
    )

    st.header("1. Recipes as baker's percentages")
    st.markdown(
        "Bakers write recipes relative to the flour, which always counts as **100%**. Every other "
        "ingredient is its weight as a percentage of the flour's weight. For example, 1,000 g of flour "
        "with 650 g of water is **65% water**.\n\n"
        "This makes recipes of any size comparable: a single pizza and a restaurant batch with the same "
        "percentages are the same dough. The app describes each recipe by:\n"
        "- **five amounts**: water, salt, yeast, fat and sugar (fat and sugar can be 0)\n"
        "- **four types**: which flour, yeast, fat and sugar it uses"
    )
    st.dataframe(
        pd.DataFrame({"Grams": [1000, 650, 25, 3], "Baker's %": ["100%", "65%", "2.5%", "0.3%"]},
                     index=["Flour", "Water", "Salt", "Yeast"]),
        width="content",
    )

    st.header("2. Each style's \"average recipe\"")
    st.markdown(
        "For each style, the app averages all of its curated recipes into one typical recipe, called "
        "the style's **centroid**. Think of it as the centre of that style: the amounts are averages, "
        "and for the types it remembers how often each one is used. The table shows the averages and "
        "the most common type of each ingredient."
    )
    st.dataframe(
        _style_averages(model),
        column_config={label(c): st.column_config.NumberColumn(format="%.2f%%") for c in NUMERIC},
    )
    st.caption(
        "Before comparing, the amounts are put on a common scale, so a 1-point change in salt "
        "(which varies little between recipes) counts for more than a 1-point change in water."
    )

    st.header("3. Affinity: how close you are to each style")
    st.markdown(
        "The app measures how far your recipe is from each style's centroid, counting both the amounts "
        "and the types. The **affinity score** turns those distances into shares that add up to 100%: "
        "the closer you are to a style, the bigger its share.\n\n"
        "Affinity is a similarity score, **not** a probability or a grade. 60% Neapolitan means your "
        "dough is nearer to the Neapolitan average than to the others, not that there is a 60% chance "
        "it is Neapolitan."
    )

    st.header("4. Style mix")
    st.markdown(
        "The bar chart on the Formulation page shows each recipe's **style mix**: the blend of the "
        "three averages that comes closest to it, such as \"70% New York, 30% Neapolitan\". The rows "
        "for your recipe, the adjusted recipe and your target sit one above the other, so you can see "
        "how the adjustment shifts the blend. It's a rough description, because the styles overlap in "
        "some ingredients."
    )

    st.header("5. Adjusting a recipe")
    st.markdown(
        "When you pick a target style (or a blend of styles), the app searches for the recipe that gets "
        "closest to the target while changing as little as possible. Changes are not all equally welcome:\n"
        "- **Nudging an amount** (a bit more water, a bit less yeast) is cheap.\n"
        "- **Swapping a type** (bread flour for Tipo 00) costs more.\n"
        "- **Dropping** fat or sugar costs about as much as a swap.\n"
        "- **Adding** an ingredient your recipe doesn't have costs the most, so it rarely happens.\n\n"
        "Suggested amounts always stay within the range seen in the curated recipes."
    )

    st.header("Limits worth knowing")
    st.markdown(
        f"- The styles are learned from only {n} recipes "
        f"({', '.join(f'{(model.recipes[Col.style] == s).sum()} {label(s)}' for s in STYLES)}). "
        "A few unusual recipes can move an average.\n"
        "- The model sees ingredients only. Oven temperature, fermentation time, kneading and pan "
        "versus stone all matter to a real pizza but aren't part of the comparison.\n"
        "- Some source recipes gave cups and teaspoons instead of grams. Those were converted with "
        "published reference weights, which are approximate."
    )
