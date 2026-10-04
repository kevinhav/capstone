"""Recipes and style centroids as a graph."""

import networkx as nx
import pandas as pd
from sklearn.neighbors import kneighbors_graph
from sklearn.pipeline import Pipeline

from capstone.config import FEATURES
from capstone.features import transform
from capstone.models.centroids import affinity, distances, styles


def build_graph(pipe: Pipeline, X: pd.DataFrame, y: pd.Series, k: int = 3) -> nx.Graph:
    """Recipes and style centroids as nodes.

    Edges: every recipe -> every centroid (kind="centroid", weighted by distance and
    affinity) and each recipe -> its k nearest recipes in feature space (kind="neighbor").

    Args:
        pipe: Fitted centroid pipeline.
        X: Recipes with the FEATURES columns.
        y: Style label per recipe.
        k: Nearest neighbors per recipe.
    """
    dist, aff = distances(pipe, X), affinity(pipe, X)
    Z = transform(pipe, X)

    G = nx.Graph()
    for style in styles(pipe):
        G.add_node(style, kind="style", style=style)
    for rid in X.index:
        G.add_node(rid, kind="recipe", style=y[rid], **X.loc[rid, FEATURES].to_dict())

    for rid in X.index:
        for style in styles(pipe):
            G.add_edge(rid, style, kind="centroid", distance=dist.loc[rid, style], affinity=aff.loc[rid, style])

    knn = kneighbors_graph(Z.values, n_neighbors=k, mode="distance")
    for i, j in zip(*knn.nonzero()):
        a, b = Z.index[i], Z.index[j]
        if not G.has_edge(a, b):
            G.add_edge(a, b, kind="neighbor", distance=knn[i, j], same_style=y[a] == y[b])
    return G
