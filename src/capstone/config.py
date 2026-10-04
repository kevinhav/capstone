from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Final


# -- paths ------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectPaths:
    """Filesystem locations anchored to the repo root, so code and notebooks
    resolve the same paths regardless of the current working directory."""

    root: Path = Path(__file__).resolve().parents[2]

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def interim(self) -> Path:
        return self.data / "interim"

    @property
    def processed(self) -> Path:
        return self.data / "processed"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def notebooks(self) -> Path:
        return self.root / "notebooks"

    @property
    def figures(self) -> Path:
        return self.root / "figures"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    # -- files --

    @property
    def recipes_json(self) -> Path:
        return self.raw / "pizza_style_template.json"

    @property
    def recipe_schema(self) -> Path:
        return self.raw / "pizza_recipe.schema.json"

    @property
    def recipes_jsonl(self) -> Path:
        return self.processed / "recipes.jsonl"

    @property
    def features_jsonl(self) -> Path:
        return self.processed / "features.jsonl"

    @property
    def centroids_json(self) -> Path:
        return self.processed / "centroids.json"


PATHS = ProjectPaths()


# -- domain enums -----------------------------------------------------------

ABSENT: Final = "none"  # type value for an optional ingredient the recipe doesn't use


class Style(StrEnum):
    neapolitan = "neapolitan"
    new_york = "new-york"
    sicilian = "sicilian"


class FlourType(StrEnum):
    all_purpose = "all-purpose"
    bread = "bread"
    high_gluten = "high-gluten"
    double_zero = "double_zero"
    semolina = "semolina"


class YeastType(StrEnum):
    active_dry = "active-dry"
    instant = "instant"
    fresh = "fresh"
    sourdough_starter = "sourdough-starter"  # includes poolish


class FatType(StrEnum):
    evoo = "extra-virgin olive oil"
    butter = "butter"
    lard = "lard"
    vegetable_oil = "vegetable oil"
    none = ABSENT


class SugarType(StrEnum):
    white = "white"
    brown = "brown"
    honey = "honey"
    none = ABSENT


STYLES: Final[list[Style]] = list(Style)


# -- canonical column names -------------------------------------------------


class Col(StrEnum):
    recipe_id = "recipe_id"
    style = "style"
    source = "source"
    raw_text = "raw_text"
    mapping = "mapping"
    flour = "flour"
    flour_type = "flour_type"
    water = "water"
    salt = "salt"
    yeast = "yeast"
    yeast_type = "yeast_type"
    fat = "fat"
    fat_type = "fat_type"
    sugar = "sugar"
    sugar_type = "sugar_type"


# lists rather than tuples so they index pandas frames directly (df[NUMERIC]); treat as read-only
NUMERIC: Final[list[Col]] = [Col.water, Col.salt, Col.yeast, Col.fat, Col.sugar]
CATEGORICAL: Final[list[Col]] = [Col.flour_type, Col.yeast_type, Col.fat_type, Col.sugar_type]
FEATURES: Final[list[Col]] = NUMERIC + CATEGORICAL
PROVENANCE: Final[list[Col]] = [Col.raw_text, Col.mapping]

# optional ingredients and the type column that records whether they're present
OPTIONAL: Final[Mapping[Col, Col]] = {Col.fat: Col.fat_type, Col.sugar: Col.sugar_type}


@dataclass(frozen=True)
class IngredientUnit:
    """An ingredient's ratio and type columns, which travel together when sampling."""

    name: str
    ratio: Col | None
    kind: Col | None

    @property
    def columns(self) -> tuple[Col, ...]:
        return tuple(c for c in (self.ratio, self.kind) if c is not None)


INGREDIENT_UNITS: Final[tuple[IngredientUnit, ...]] = (
    IngredientUnit("flour", None, Col.flour_type),
    IngredientUnit("water", Col.water, None),
    IngredientUnit("salt", Col.salt, None),
    IngredientUnit("yeast", Col.yeast, Col.yeast_type),
    IngredientUnit("fat", Col.fat, Col.fat_type),
    IngredientUnit("sugar", Col.sugar, Col.sugar_type),
)

FLOUR_BASIS: Final = 100.0  # baker's percentages are expressed relative to flour = 100


# -- shared types -----------------------------------------------------------

type StyleMix = Mapping[Style | str, float]
type Target = Style | str | StyleMix


# -- tunable configs --------------------------------------------------------


@dataclass(frozen=True)
class LossWeights:
    """Relative strictness of each kind of change made by the recipe adjuster.
    Defaults give a roughly 1 : 10 : 100 hierarchy between ratio tweaks, type
    swaps, and brand-new ingredients."""

    target: float = 1.0  # pull toward the target centroid
    ratio: float = 0.1  # per squared z-unit change to a main ingredient ratio (lenient)
    type_change: float = 1.0  # per ingredient whose type is swapped (moderate)
    remove: float = 1.0  # per optional ingredient dropped
    add: float = 10.0  # per optional ingredient not in the original (very strict)


@dataclass(frozen=True)
class CVConfig:
    """Repeated stratified k-fold settings. Sicilian has n = 9, so keep n_splits <= 5."""

    n_splits: int = 5
    n_repeats: int = 20
    seed: int = 0


@dataclass(frozen=True)
class FrankensteinConfig:
    """Size and seed of a synthetic recipe set built by recombining real recipes."""

    n: int = 300
    seed: int = 0


@dataclass(frozen=True)
class PlotConfig:
    style_colors: Mapping[Style, str] = field(
        default_factory=lambda: {Style.neapolitan: "tab:red", Style.new_york: "tab:blue", Style.sicilian: "tab:green"}
    )
    original_color: str = "tab:blue"
    adjusted_color: str = "tab:orange"
    target_color: str = "gray"


PLOT = PlotConfig()


@dataclass(frozen=True)
class ArtifactNames:
    """File stems for pickled models under PATHS.models."""

    style_centroids: str = "style_centroids"


ARTIFACTS = ArtifactNames()
