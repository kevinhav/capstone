"""The app's pages, defined once so pages can link to each other."""

import streamlit as st

from capstone.app.views import browser, formulation, guide

FORMULATION = st.Page(formulation.render, title="Formulation", icon=":material/tune:", url_path="formulation", default=True)
BROWSER = st.Page(browser.render, title="Recipe browser", icon=":material/table_view:", url_path="recipes")
GUIDE = st.Page(guide.render, title="How does this work?", icon=":material/help:", url_path="how-it-works")
PAGES = [FORMULATION, BROWSER, GUIDE]
