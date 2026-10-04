"""Formulation: edit a dough, adjust it toward a style or blend of styles, and scale it to a batch."""

import math
from typing import Final

import pandas as pd
import streamlit as st

from capstone.app.common import BASE_RECIPE_KEY, DEFAULT_RECIPE, INGREDIENT_ORDER, AppModel, label, load_model
from capstone.app.plots import chart_height, mix_bars
from capstone.config import (
    CATEGORICAL,
    OPTIONAL,
    NUMERIC,
    PLOT,
    STYLE_SIZES,
    STYLES,
    Col,
    FatType,
    FlourType,
    PanShape,
    Style,
    SugarType,
    YeastType,
)
from capstone.data import (
    MASS_TO_GRAMS,
    SALT_DENSITY_G_PER_TSP,
    YEAST_DENSITY_G_PER_TSP,
    Recipe,
    dough_ball_grams,
    scale_recipe,
)
from capstone.models import Adjustment, adjust, affinity, estimate_mix, target_distance

BLEND: Final = "blend"
ORIGINAL: Final = "original"
ADJUSTED: Final = "adjusted"
VERSION_LABELS: Final = {ORIGINAL: "Your recipe", ADJUSTED: "Adjusted"}

HELP: Final[dict[Col, str]] = {
    Col.water: "Hydration. More water makes a softer, wetter dough that's harder to handle.",
    Col.salt: "Seasons the dough and tightens the gluten. Most pizza doughs use 2-3%.",
    Col.yeast: "How much leavening. Less yeast usually goes with a longer, slower rise.",
    Col.fat: "Oil, butter or lard. Makes the crust more tender; 0% means none.",
    Col.sugar: "Helps browning in cooler home ovens; 0% means none.",
}


def range_warning(model: AppModel, col: Col, value: float) -> str:
    """Why an amount is unusual, or "" if it's within the range of the curated recipes.
    Leaving out fat or sugar (0%) is never unusual."""
    if col in OPTIONAL and value == 0:
        return ""
    if value < model.low[col]:
        return f"Lower than any curated recipe (lowest {model.low[col]:.2f}%)"
    if value > model.high[col]:
        return f"Higher than any curated recipe (highest {model.high[col]:.2f}%)"
    return ""


def _and_join(words: list[str]) -> str:
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def _recipe_inputs(model: AppModel) -> Recipe:
    recipes = model.recipes
    options = list(recipes.index)
    current = st.session_state.get(BASE_RECIPE_KEY, DEFAULT_RECIPE)
    base_id = st.selectbox(
        "Start from",
        options,
        index=options.index(current),
        format_func=lambda r: f"{r} ({label(recipes.loc[r, Col.style])})",
        help="A curated recipe to start from. Change any value below to make it your own.",
    )
    st.session_state[BASE_RECIPE_KEY] = base_id
    base = Recipe.from_row(recipes.loc[base_id])

    # widget keys include the base recipe so picking a new one resets every input
    def pick[E](col: Col, enum: type[E], current: E) -> E:
        options = list(enum)
        return st.selectbox(label(col), options, index=options.index(current), format_func=label, key=f"{base_id}-{col}")

    def amount(col: Col, current: float, step: float, ignored: bool = False) -> float:
        value = st.number_input(
            f"{label(col)} %", min_value=0.0, value=float(current), step=step, format="%.2f",
            help=f"{HELP[col]} Curated recipes {'that use it ' if col in OPTIONAL else ''}have "
            f"{model.low[col]:.2f}–{model.high[col]:.2f}%.",
            key=f"{base_id}-{col}-amt",
        )
        if ignored and value > 0:
            st.caption(f":orange[:material/warning: Ignored until you choose a {label(col).lower()} type]")
        elif not ignored and (warning := range_warning(model, col, value)):
            st.caption(f":orange[:material/warning: {warning}]")
        return value

    # one row per ingredient (amount beside its type) so narrow screens stack them in order
    flour_type = pick(Col.flour_type, FlourType, base.flour_type)
    left, right = st.columns(2)
    with left:
        water = amount(Col.water, base.water, 1.0)
    with right:
        salt = amount(Col.salt, base.salt, 0.1)
    left, right = st.columns(2)
    with left:
        yeast = amount(Col.yeast, base.yeast, 0.05)
    with right:
        yeast_type = pick(Col.yeast_type, YeastType, base.yeast_type)
    # optional ingredients: the type is picked first so the amount knows whether it counts
    left, right = st.columns(2)
    with right:
        fat_type = pick(Col.fat_type, FatType, base.fat_type)
    with left:
        fat = amount(Col.fat, base.fat, 0.5, ignored=fat_type == FatType.none)
    left, right = st.columns(2)
    with right:
        sugar_type = pick(Col.sugar_type, SugarType, base.sugar_type)
    with left:
        sugar = amount(Col.sugar, base.sugar, 0.5, ignored=sugar_type == SugarType.none)

    # Recipe treats a 0 amount or a "none" type as the ingredient being absent
    return Recipe(
        flour_type=flour_type, water=water, salt=salt, yeast=yeast, yeast_type=yeast_type,
        fat=fat, fat_type=fat_type, sugar=sugar, sugar_type=sugar_type, recipe_id=ORIGINAL,
    )


def _target_inputs() -> dict[str, float]:
    """Target shares per style; empty if no target is chosen."""
    choice = st.segmented_control(
        "Aim for", [*STYLES, BLEND], default=Style.neapolitan,
        format_func=lambda s: "Blend" if s == BLEND else label(s),
        help="The suggested changes below move your dough toward this style, or toward a mix of styles.",
    )
    if choice is None:
        return {}
    if choice != BLEND:
        return {str(choice): 100.0}
    defaults = {Style.neapolitan: 50, Style.new_york: 50, Style.sicilian: 0}
    shares = {
        str(s): float(col.slider(label(s), 0, 100, defaults[s], 5, format="%d%%"))
        for col, s in zip(st.columns(len(STYLES)), STYLES)
    }
    total = sum(shares.values())
    if total:
        st.caption("Blend: " + ", ".join(f"{v / total:.0%} {label(s)}" for s, v in shares.items() if v))
    return {s: v for s, v in shares.items() if v}


def _change(col: Col, before: object, after: object) -> str:
    if col in CATEGORICAL:
        return "" if before == after else "swapped"
    if before == 0 and after > 0:
        return "added"
    if before > 0 and after == 0:
        return "removed"
    diff = float(after) - float(before)
    return f"{diff:+.2f}" if abs(diff) >= 0.005 else ""


def _changes_table(frame: pd.DataFrame) -> pd.DataFrame:
    before, after = frame.loc[ORIGINAL], frame.loc[ADJUSTED]

    def show(col: Col, v: object) -> str:
        return f"{v:.2f}%" if col in NUMERIC else label(v)

    return pd.DataFrame(
        {
            VERSION_LABELS[ORIGINAL]: [show(c, before[c]) for c in INGREDIENT_ORDER],
            VERSION_LABELS[ADJUSTED]: [show(c, after[c]) for c in INGREDIENT_ORDER],
            "Change": [_change(c, before[c], after[c]) for c in INGREDIENT_ORDER],
        },
        index=[label(c) for c in INGREDIENT_ORDER],
    )


def _summary(result: Adjustment, n_amounts: int) -> str:
    parts = [
        f"{n_amounts} amount(s) nudged",
        f"{result.n_type_changes} type(s) swapped",
        f"{result.n_removed} ingredient(s) dropped",
        f"{result.n_added} added",
    ]
    return ", ".join(parts) + "."


def _results(model: AppModel, recipe: pd.Series, shares: dict[str, float]) -> pd.Series:
    """Adjust toward the target and show affinity, style mix, and the changes. Returns the adjusted recipe."""
    result = adjust(recipe, shares, model.space)
    frame = pd.DataFrame([recipe, result.recipe.rename(ADJUSTED)])
    aff = affinity(model.pipe, frame)
    mixes = estimate_mix(model.pipe, frame)
    dist = target_distance(model.pipe, frame, shares)

    st.subheader("Style affinity")
    st.caption("How close each version is to each style's average recipe. Shares add up to 100%; higher means closer.")
    for col, style in zip(st.columns(len(STYLES)), STYLES):
        before, after = aff.loc[ORIGINAL, style], aff.loc[ADJUSTED, style]
        col.metric(
            label(style), f"{after:.0%}", f"{round((after - before) * 100):+d} pts from yours",
            delta_color="off", border=True,
        )

    chart, table = st.columns([1, 1], gap="medium")
    with chart:
        st.markdown("**Style mix**")
        dark = st.context.theme.type == "dark"
        colors = PLOT.style_colors_dark if dark else PLOT.style_colors
        total = sum(shares.values())
        bars = pd.DataFrame(
            {label(s): [mixes.loc[ORIGINAL, s], mixes.loc[ADJUSTED, s], shares.get(str(s), 0) / total] for s in STYLES},
            index=[VERSION_LABELS[ORIGINAL], VERSION_LABELS[ADJUSTED], "Target"],
        )
        st.altair_chart(
            mix_bars(bars, {label(s): colors[s] for s in STYLES}, PLOT.surface_dark if dark else PLOT.surface),
            width="stretch", height=chart_height(len(bars)),
        )
        st.caption("Each bar splits a recipe into the blend of style averages that best matches it.")
    with table:
        st.markdown("**Suggested changes**")
        changes = _changes_table(frame)
        n_amounts = sum(
            1 for c in NUMERIC if _change(c, frame.loc[ORIGINAL, c], frame.loc[ADJUSTED, c]) not in ("", "added", "removed")
        )
        if (changes["Change"] == "").all():
            st.success("Your recipe is already as close to the target as small changes can get it.")
        st.dataframe(changes, width="stretch", height="content")
        st.caption(
            f"{_summary(result, n_amounts)} Distance to target: {dist[ORIGINAL]:.2f} → {dist[ADJUSTED]:.2f} "
            "(lower is closer)."
        )
    return result.recipe


def _volume_hint(col: Col, grams: float, recipe: pd.Series) -> str:
    """Approximate teaspoons for small dry ingredients, where a source density is known."""
    if col == Col.salt:
        return f"≈ {grams / SALT_DENSITY_G_PER_TSP['table']:.1f} tsp table salt"
    if col == Col.yeast and (density := YEAST_DENSITY_G_PER_TSP.get(YeastType(recipe[Col.yeast_type]))):
        return f"≈ {grams / density:.1f} tsp"
    return ""


def _ball_weight(style: Style, key: str) -> float:
    """Grams per dough ball, from a pizza size and thickness factor or typed in directly."""
    size_by = st.segmented_control(
        "Size by", ["pizza", "weight"], default="pizza", required=True,
        format_func={"pizza": "Pizza size", "weight": "Ball weight"}.get, key=f"{key}-size-by",
    )
    if size_by == "weight":
        return st.number_input("Grams per ball", min_value=50, max_value=3000, value=250, step=10, key=f"{key}-grams")

    size = STYLE_SIZES[style]
    references = "\n".join(
        f"- {label(s)}: {p.factor_low:.3f}–{p.factor_high:.3f}" + (" (home oven)" if s == Style.neapolitan else "")
        for s, p in STYLE_SIZES.items()
    )
    factor_col, shape_col = st.columns(2)
    factor = factor_col.number_input(
        "Thickness factor (oz per sq in)", min_value=0.03, max_value=0.20, value=size.factor, step=0.0025,
        format="%.4f", key=f"{key}-factor",
        help=f"Ounces of dough per square inch of pizza. Higher makes a thicker crust. Typical ranges:\n\n{references}",
    )
    shape = shape_col.segmented_control(
        "Pan", list(PanShape), default=size.shape, required=True, key=f"{key}-shape",
        format_func={PanShape.round: "Round", PanShape.rectangle: "Rectangular"}.get,
    )
    first_dim, second_dim = st.columns(2)
    if shape == PanShape.round:
        diameter = first_dim.number_input("Diameter (in)", 4.0, 36.0, size.diameter, 1.0, key=f"{key}-diameter")
        area, described = math.pi * (diameter / 2) ** 2, f"{diameter:g}-inch round"
    else:
        length = first_dim.number_input("Length (in)", 4.0, 36.0, size.length, 1.0, key=f"{key}-length")
        width = second_dim.number_input("Width (in)", 4.0, 36.0, size.width, 1.0, key=f"{key}-width")
        area, described = length * width, f"{length:g} × {width:g} inch pan"
    grams = dough_ball_grams(factor, area)
    st.caption(
        f"Each ball: **{grams:,.0f} g** ({grams / MASS_TO_GRAMS['oz']:.1f} oz). "
        f"Pizza: {described} ({area:,.0f} sq in) at {factor:g} oz per sq in."
    )
    return grams


def _batch(versions: dict[str, pd.Series], styles: dict[str, Style]) -> None:
    st.header("Make a batch")
    st.caption("Turn the percentages into weights. Weighing with a kitchen scale is far more accurate than spoons and cups.")
    which, balls = st.columns(2)
    version = which.segmented_control(
        "Recipe", list(versions), default=list(versions)[-1], format_func=VERSION_LABELS.get, required=True,
    )
    n = balls.number_input("Dough balls", min_value=1, max_value=100, value=4, step=1)
    # keyed by style so the size defaults follow the style of the recipe being scaled
    weight = _ball_weight(styles[version], key=f"batch-{styles[version]}")
    recipe = versions[version]
    grams = scale_recipe(recipe, n * weight)
    present = [c for c in grams.index if c == Col.flour or recipe[c] > 0]
    kinds = {Col.flour: Col.flour_type, Col.yeast: Col.yeast_type, Col.fat: Col.fat_type, Col.sugar: Col.sugar_type}
    batch = pd.DataFrame(
        {
            "Type": [label(recipe[kinds[c]]) if c in kinds else "" for c in present],
            "Baker's %": [100.0 if c == Col.flour else float(recipe[c]) for c in present],
            "Grams": [grams[c] for c in present],
            "Approx. volume": [_volume_hint(c, grams[c], recipe) for c in present],
        },
        index=pd.Index([label(c) for c in present], name="Ingredient"),
    )
    st.dataframe(
        batch,
        column_config={
            "Baker's %": st.column_config.NumberColumn(format="%.2f%%"),
            "Grams": st.column_config.NumberColumn(format="%.1f g"),
        },
        width="content",
    )
    st.caption(f"Total dough: {grams.sum():,.0f} g. Volumes are rough guides from published reference weights.")
    st.download_button(
        "Download as CSV", batch.to_csv().encode(), file_name=f"pizza_dough_{version}.csv", mime="text/csv",
        icon=":material/download:",
    )


def render() -> None:
    from capstone.app import nav  # deferred: nav imports this module

    model = load_model()
    st.title("Formulation")
    st.markdown(
        "Start from a curated recipe or type in your own, choose a style to aim for, and see the "
        "smallest changes that get your dough there. All amounts are baker's percentages (flour = 100%)."
    )
    st.page_link(nav.GUIDE, label="New here? How does this work?", icon=":material/help:")

    st.header("Target style")
    st.caption("Pick the style you want your dough to be more like. Everything below compares your dough with it.")
    shares = _target_inputs()

    inputs, results = st.columns([1, 2], gap="large")
    with inputs:
        st.header("Your dough")
        recipe = _recipe_inputs(model).to_row()
    versions = {ORIGINAL: recipe}
    styles = {ORIGINAL: Style(model.recipes.loc[st.session_state[BASE_RECIPE_KEY], Col.style])}
    with results:
        unusual = [label(c).lower() for c in NUMERIC if range_warning(model, c, recipe[c])]
        if unusual:
            st.warning(
                f"Your {_and_join(unusual)} {'is' if len(unusual) == 1 else 'are'} outside the range of the curated "
                "recipes, so the comparison below is less reliable. Suggested amounts always stay within that range.",
                icon=":material/warning:",
            )
        if shares:
            versions[ADJUSTED] = _results(model, recipe, shares)
            styles[ADJUSTED] = Style(max(shares, key=shares.get))  # a blend sizes like its largest style
        else:
            st.info("Choose a target style (or a blend) above to see suggested changes.")
    st.divider()
    _batch(versions, styles)
