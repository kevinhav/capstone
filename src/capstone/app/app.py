"""Streamlit entry point: `uv run streamlit run src/capstone/app/app.py`."""

import streamlit as st

from capstone.app.nav import PAGES


def main() -> None:
    st.set_page_config(page_title="Pizza dough formulation", page_icon=":material/local_pizza:", layout="wide")
    st.navigation(PAGES, position="top").run()


main()
