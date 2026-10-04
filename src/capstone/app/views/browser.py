"""Recipe browser: the curated recipes as a filterable table, with each recipe's source text."""

import pandas as pd
import streamlit as st

from capstone.app.common import BASE_RECIPE_KEY, INGREDIENT_ORDER, AppModel, label, load_model
from capstone.config import CATEGORICAL, NUMERIC, STYLES, Col

COLUMNS = [Col.recipe_id, Col.style, *INGREDIENT_ORDER, Col.source]


def _table(model: AppModel, styles: list[str]) -> pd.DataFrame:
    shown = model.recipes[model.recipes[Col.style].isin(styles)].reset_index()
    return shown.assign(**{str(c): shown[c].map(label) for c in [Col.style, *CATEGORICAL]})[COLUMNS]


def _column_config() -> dict[str, object]:
    amounts = {
        str(c): st.column_config.NumberColumn(label(c), format="%.2f%%" if c == Col.yeast else "%.1f%%")
        for c in NUMERIC
    }
    types = {str(c): st.column_config.TextColumn(label(c)) for c in CATEGORICAL}
    types[Col.yeast_type] = st.column_config.TextColumn(label(Col.yeast_type), width="medium")  # fits "Sourdough / poolish"
    return {
        Col.recipe_id: st.column_config.TextColumn("Recipe"),
        Col.style: st.column_config.TextColumn("Style"),
        **amounts,
        **types,
        Col.source: st.column_config.LinkColumn("Source", display_text=r"https?://(?:www\.)?([^/]+)"),
    }


def _open_in_formulation(recipe_id: str) -> None:
    from capstone.app import nav  # deferred: nav imports this module

    st.session_state[BASE_RECIPE_KEY] = recipe_id
    st.switch_page(nav.FORMULATION)


def render() -> None:
    model = load_model()
    st.title("Recipe browser")
    st.markdown(
        "The curated recipes the app learns from, in baker's percentages (flour = 100%). "
        "Select a row to see the original recipe text or to open it on the Formulation page."
    )
    styles = st.pills("Style", STYLES, selection_mode="multi", default=STYLES, format_func=label) or []
    shown = _table(model, styles)
    event = st.dataframe(
        shown, column_config=_column_config(), hide_index=True, on_select="rerun", selection_mode="single-row",
        height="content",
    )
    st.caption(f"Showing {len(shown)} of {len(model.recipes)} recipes. Fat and sugar are 0% when a recipe doesn't use them.")

    if not event.selection.rows:
        return
    recipe_id = str(shown.iloc[event.selection.rows[0]][Col.recipe_id])
    st.subheader(recipe_id)
    if st.button("Open in Formulation", icon=":material/tune:", type="primary"):
        _open_in_formulation(recipe_id)
    with st.expander("Original recipe text", expanded=True):
        st.text(model.provenance.loc[recipe_id, Col.raw_text])
        st.caption(f"Source: {model.recipes.loc[recipe_id, Col.source]}")
