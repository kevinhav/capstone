"""Recipe data contract, unit/ingredient conversions, loading, and synthetic recipes."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from capstone.config import (
    ABSENT,
    CATEGORICAL,
    FEATURES,
    FLOUR_BASIS,
    INGREDIENT_UNITS,
    OPTIONAL,
    PATHS,
    PROVENANCE,
    Col,
    FatType,
    FlourType,
    FrankensteinConfig,
    Style,
    SugarType,
    YeastType,
)

# -- recipe contract --------------------------------------------------------


@dataclass(kw_only=True)
class Recipe:
    """One dough formulation in baker's percentages (flour = 100)."""

    flour_type: FlourType
    water: float
    salt: float
    yeast: float
    yeast_type: YeastType
    fat: float = 0.0
    fat_type: FatType = FatType.none
    sugar: float = 0.0
    sugar_type: SugarType = SugarType.none
    flour: float = FLOUR_BASIS
    style: Style | None = None
    source: str = ""
    recipe_id: str = "recipe"

    def __post_init__(self) -> None:
        # an optional ingredient is absent if either its amount is 0 or its type is "none"
        if self.fat == 0 or self.fat_type == FatType.none:
            self.fat, self.fat_type = 0.0, FatType.none
        if self.sugar == 0 or self.sugar_type == SugarType.none:
            self.sugar, self.sugar_type = 0.0, SugarType.none

    def to_row(self) -> pd.Series:
        """The recipe's model features as a Series named by recipe_id."""
        values = asdict(self)
        return pd.Series({c: str(values[c]) if c in CATEGORICAL else float(values[c]) for c in FEATURES}, name=self.recipe_id)

    @classmethod
    def from_row(cls, row: pd.Series) -> "Recipe":
        """Build a Recipe from a row of `load_recipes()` (or any frame with the feature columns)."""
        return cls(
            flour_type=FlourType(row[Col.flour_type]),
            water=float(row[Col.water]),
            salt=float(row[Col.salt]),
            yeast=float(row[Col.yeast]),
            yeast_type=YeastType(row[Col.yeast_type]),
            fat=float(row[Col.fat]),
            fat_type=FatType(row[Col.fat_type]),
            sugar=float(row[Col.sugar]),
            sugar_type=SugarType(row[Col.sugar_type]),
            style=Style(row[Col.style]) if Col.style in row and pd.notna(row[Col.style]) else None,
            source=str(row.get(Col.source, "")),
            recipe_id=str(row.name),
        )


# -- unit conversions -------------------------------------------------------

MASS_TO_GRAMS: dict[str, float] = {
    "g": 1.0,
    "oz": 28.3495,
    "lb": 453.592,
    "kg": 1000.0,
}

VOLUME_TO_ML: dict[str, float] = {
    "ml": 1.0,
    "l": 1000.0,
    "tsp": 4.92892,
    "tbsp": 14.7868,
    "cup": 236.588,
    "fl_oz": 29.5735,
}

# grams per mL, for converting a volume of a liquid ingredient to weight
INGREDIENT_DENSITY_G_PER_ML: dict[str, float] = {
    "water": 1.00,
    "olive_oil": 0.91,
    "honey": 1.42,
    "sugar_white": 0.845,  # granulated
    "sugar_brown": 0.93,  # packed
}

# dry yeast is usually measured by volume in source recipes; g per tsp
YEAST_DENSITY_G_PER_TSP: dict[YeastType, float] = {
    YeastType.instant: 3.1,
    YeastType.active_dry: 3.3,
}

# for the rare source recipe that measures flour by volume with no gram weight given at all
FLOUR_DENSITY_G_PER_CUP: dict[FlourType, float] = {
    FlourType.all_purpose: 125.0,
    FlourType.bread: 127.0,
    FlourType.high_gluten: 130.0,
    FlourType.double_zero: 130.0,
    FlourType.semolina: 167.0,
}

# salt density varies enough by brand/grind to matter when only a volume is given
SALT_DENSITY_G_PER_TSP: dict[str, float] = {
    "table": 6.0,
    "diamond_crystal_kosher": 2.8,
    "mortons_kosher": 4.8,
}

# multiplier to convert a gram amount of this yeast type into its instant-dry-yeast
# equivalent (grams_instant = grams_x * ratio)
YEAST_TO_INSTANT_RATIO: dict[YeastType, float] = {
    YeastType.instant: 1.0,
    YeastType.active_dry: 0.8,  # ADY = IDY * 1.25
    YeastType.fresh: 1 / 3,  # fresh = IDY * 3
    # sourdough_starter has no fixed ratio - handled via mass-balance, not scaling
}

# poolish is equal parts flour and water by weight; also the default assumed hydration
# for a sourdough starter whose own hydration isn't stated in the source recipe
DEFAULT_STARTER_HYDRATION_PCT: float = 100.0


# -- raw text -> canonical enum ---------------------------------------------

FLOUR_TYPE_ALIASES: dict[str, FlourType] = {
    "00": FlourType.double_zero,
    "tipo 00": FlourType.double_zero,
    "caputo": FlourType.double_zero,
    "pizza flour": FlourType.double_zero,
    "bread flour": FlourType.bread,
    "high gluten": FlourType.high_gluten,
    "high-gluten": FlourType.high_gluten,
    "kyrol": FlourType.high_gluten,
    "bromated": FlourType.high_gluten,
    "all-purpose": FlourType.all_purpose,
    "all purpose": FlourType.all_purpose,
    "lancelot": FlourType.high_gluten,
    "all trumps": FlourType.high_gluten,
    "semolina": FlourType.semolina,
    "semola": FlourType.semolina,
    "other": FlourType.all_purpose,  # fallback for unknown flours
}

YEAST_TYPE_ALIASES: dict[str, YeastType] = {
    "instant": YeastType.instant,
    "idy": YeastType.instant,
    "rapid-rise": YeastType.instant,
    "rapid rise": YeastType.instant,
    "active dry": YeastType.active_dry,
    "ady": YeastType.active_dry,
    "fresh": YeastType.fresh,
    "compressed": YeastType.fresh,
    "cake yeast": YeastType.fresh,
    "sourdough": YeastType.sourdough_starter,
    "starter": YeastType.sourdough_starter,
    "poolish": YeastType.sourdough_starter,
    "culture": YeastType.sourdough_starter,
    "mother yeast": YeastType.sourdough_starter,
    "preferment": YeastType.sourdough_starter,
    "other": YeastType.instant,  # fallback for unknown yeasts
}

FAT_TYPE_ALIASES: dict[str, FatType] = {
    "evoo": FatType.evoo,
    "extra-virgin olive oil": FatType.evoo,
    "extra virgin olive oil": FatType.evoo,
    "olive oil": FatType.evoo,
    "butter": FatType.butter,
    "lard": FatType.lard,
    "strutto": FatType.lard,
    "vegetable oil": FatType.vegetable_oil,
    "soybean oil": FatType.vegetable_oil,
    "other": FatType.evoo,  # fallback for unknown fats
}

SUGAR_TYPE_ALIASES: dict[str, SugarType] = {
    "honey": SugarType.honey,
    "brown sugar": SugarType.brown,
    "granulated sugar": SugarType.white,
    "sugar": SugarType.white,
    "white sugar": SugarType.white,
    "other": SugarType.white,  # fallback for unknown sugars
}


def split_starter(total_g: float, hydration_pct: float = DEFAULT_STARTER_HYDRATION_PCT) -> tuple[float, float]:
    """Split a preferment's (poolish, sourdough starter, etc.) total weight into its
    (flour_g, water_g) components, to be folded into the main dough's totals.

    Args:
        total_g: Total preferment weight in grams.
        hydration_pct: Water as a percentage of flour, e.g. 100 for a poolish.

    Returns:
        (flour_g, water_g)
    """
    flour_g = total_g / (1 + hydration_pct / 100)
    return flour_g, total_g - flour_g


def match_alias[T](text: str, aliases: dict[str, T]) -> T | None:
    """Match raw ingredient text against an alias table, preferring the longest (most
    specific) matching key so e.g. "brown sugar" wins over the bare "sugar" fallback.

    Returns:
        The matched canonical value, or None if no alias appears in the text.
    """
    text = text.lower()
    for key in sorted(aliases, key=len, reverse=True):
        if key in text:
            return aliases[key]
    return None


def to_grams(amount: float, unit: str, density_g_per_ml: float | None = None) -> float:
    """Convert a mass or volume amount to grams.

    Args:
        amount: Quantity in `unit`.
        unit: A key of MASS_TO_GRAMS or VOLUME_TO_ML.
        density_g_per_ml: Required for volume units (see INGREDIENT_DENSITY_G_PER_ML).

    Raises:
        ValueError: For an unknown unit, or a volume unit without a density.
    """
    if unit in MASS_TO_GRAMS:
        return amount * MASS_TO_GRAMS[unit]
    if unit in VOLUME_TO_ML:
        if density_g_per_ml is None:
            raise ValueError(f"density_g_per_ml required to convert volume unit '{unit}' to grams")
        return amount * VOLUME_TO_ML[unit] * density_g_per_ml
    raise ValueError(f"unrecognized unit: {unit}")


def to_baker_percentage(ingredient_g: float, flour_g: float) -> float:
    """Express an ingredient's weight as a percentage of total flour weight."""
    return ingredient_g / flour_g * FLOUR_BASIS


# -- loading ----------------------------------------------------------------


def _read_raw(path: Path) -> pd.DataFrame:
    return pd.DataFrame(json.loads(path.read_text()))


def _drop_provenance(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=PROVENANCE)


def _fill_absent_types(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(**{str(c): df[c].fillna(ABSENT) for c in OPTIONAL.values()})


def _index_by_id(df: pd.DataFrame) -> pd.DataFrame:
    return df.set_index(Col.recipe_id.value)


def load_recipes(path: Path = PATHS.recipes_json) -> pd.DataFrame:
    """Load the curated recipes as one row per recipe, indexed by recipe_id.

    Provenance fields (raw_text, mapping) are dropped and absent optional-ingredient
    types are filled with "none" so every feature column is populated.

    Args:
        path: Curated recipe JSON (a list of objects matching the recipe schema).
    """
    df = _read_raw(path).pipe(_drop_provenance).pipe(_fill_absent_types).pipe(_index_by_id)
    logger.debug("loaded {} recipes from {}", len(df), path)
    return df


def load_provenance(path: Path = PATHS.recipes_json) -> pd.DataFrame:
    """Raw source text and per-field conversion mapping for each recipe, indexed by recipe_id."""
    return _read_raw(path).pipe(_index_by_id)[PROVENANCE]


# -- synthetic recipes ------------------------------------------------------


def make_frankensteins(recipes: pd.DataFrame, config: FrankensteinConfig = FrankensteinConfig()) -> pd.DataFrame:
    """Synthetic recipes built by drawing each ingredient unit (ratio + its type) from an
    independently chosen real recipe.

    Fat and sugar keep their type with them, so 'no fat' stays consistent with a fat type
    of 'none'. Donor recipe ids and styles are recorded per unit, plus how many distinct
    styles contributed.

    Args:
        recipes: Output of `load_recipes()`.
        config: Number of recipes and random seed.
    """
    rng = np.random.default_rng(config.seed)
    rows = []
    for _ in range(config.n):
        row: dict[str, object] = {Col.flour.value: FLOUR_BASIS}
        for unit in INGREDIENT_UNITS:
            donor = recipes.iloc[rng.integers(len(recipes))]
            row |= {str(c): donor[c] for c in unit.columns}
            row[f"donor_{unit.name}"] = donor.name
            row[f"donor_{unit.name}_style"] = donor[Col.style]
        rows.append(row)
    out = pd.DataFrame(rows, index=pd.Index([f"frank_{i:04d}" for i in range(config.n)], name=Col.recipe_id.value))
    donor_styles = out[[f"donor_{u.name}_style" for u in INGREDIENT_UNITS]]
    return out.assign(n_donor_styles=donor_styles.nunique(axis=1))
