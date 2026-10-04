"""Build and cache the project's fitted model and processed data outputs."""

from loguru import logger
from sklearn.pipeline import Pipeline

from capstone.config import PATHS
from capstone.data import load_recipes
from capstone.features import transform
from capstone.models.centroids import centroid_profile, load_or_fit_centroids
from capstone.utilities import write_json, write_jsonl


def build_artifacts() -> Pipeline:
    """Fit (or load) the centroid pipeline and write the processed outputs:
    recipes.jsonl, features.jsonl (transformed space), and centroids.json."""
    recipes = load_recipes()
    pipe = load_or_fit_centroids(recipes)
    write_jsonl(recipes, PATHS.recipes_jsonl)
    write_jsonl(transform(pipe, recipes), PATHS.features_jsonl)
    write_json(centroid_profile(recipes, pipe), PATHS.centroids_json)
    logger.info("artifacts written to {}", PATHS.processed)
    return pipe
