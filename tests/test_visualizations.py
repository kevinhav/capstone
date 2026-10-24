"""Every report figure function renders on the real recipes without error."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from sklearn.metrics import pairwise_distances

from capstone import visualizations as viz
from capstone.config import STYLES, Col, FrankensteinConfig
from capstone.data import load_recipes, make_frankensteins
from capstone.features import transform
from capstone.models import adjust_many, build_graph, build_search_space, distances, estimate_mix, fit_centroids


@pytest.fixture(scope="module")
def setup():
    viz.set_theme()
    recipes = load_recipes()
    pipe = fit_centroids(recipes, recipes[Col.style])
    return recipes, pipe


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def test_set_theme_registers_colormaps(setup):
    assert "capstone_sequential" in matplotlib.colormaps
    assert "capstone_diverging_r" in matplotlib.colormaps
    viz.set_theme()  # idempotent


def test_figsize():
    assert viz.figsize("full", 0.5) == (viz.FULL_WIDTH, viz.FULL_WIDTH / 2)
    assert viz.figsize(4.0, 0.25) == (4.0, 1.0)


def test_data_figures(setup):
    recipes, pipe = setup
    assert isinstance(viz.feature_distributions(recipes), Figure)
    assert isinstance(viz.category_shares(recipes), Figure)
    Z = transform(pipe, recipes)
    square = pd.DataFrame(pairwise_distances(Z), Z.index, Z.index)
    assert isinstance(viz.distance_matrix(square, recipes[Col.style]), Figure)
    assert isinstance(viz.centroid_heatmap(pipe), Figure)


def test_model_figures(setup):
    recipes, pipe = setup
    coords = pd.DataFrame(np.random.default_rng(0).normal(size=(len(recipes), 2)), recipes.index, ["PC1", "PC2"])
    assert isinstance(viz.style_scatter(coords, recipes[Col.style]), Figure)
    G = build_graph(pipe, recipes, recipes[Col.style])
    assert isinstance(viz.recipe_network(G, "centroid"), Figure)
    assert isinstance(viz.recipe_network(G, "neighbor"), Figure)
    folds = pd.DataFrame({"model": ["a", "a", "b", "b"], "accuracy": [0.5, 0.7, 0.6, 0.8]})
    assert isinstance(viz.cv_scores(folds, highlight="a", reference=0.4), Figure)
    y = recipes[Col.style].astype(str)
    cm = viz.confusion_frame(y, y)
    assert cm.to_numpy().trace() == len(y)
    assert isinstance(viz.confusion_matrices({"x": cm, "y": cm}), Figure)
    assert isinstance(viz.importance_plot(pd.Series([0.1, 0.3], ["water", "salt"])), Figure)


def test_adjustment_figures(setup):
    recipes, pipe = setup
    frank = make_frankensteins(recipes, FrankensteinConfig(n=10, seed=0))
    space = build_search_space(pipe, recipes)
    adjusted, _ = adjust_many(frank, "neapolitan", space)
    pairs = {"neapolitan": (distances(pipe, frank)["neapolitan"], distances(pipe, adjusted)["neapolitan"])}
    assert isinstance(viz.before_after(pairs), Figure)
    mixes = estimate_mix(pipe, frank)
    assert isinstance(viz.style_mix(mixes.head(3)), Figure)
    assert isinstance(viz.ternary(mixes, mixes), Figure)
    sweep = pd.DataFrame({"a": [0.1, 0.5, 0.9], "b": [0.0, 0.0, 0.0]}, index=[0.5, 1.0, 2.0])
    assert isinstance(viz.line_plot(sweep, percent=True, xscale="log"), Figure)


def test_line_plot_refuses_too_many_series():
    with pytest.raises(ValueError):
        viz.line_plot(pd.DataFrame(np.zeros((3, 5))))


def test_every_style_has_a_color():
    assert all(viz.style_color(s).startswith("#") for s in STYLES)
