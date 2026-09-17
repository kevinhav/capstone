from dataclasses import dataclass
from enum import Enum


class FlourType(Enum):
    all_purpose = "all-purpose"
    bread = "bread"
    high_gluten = "high-gluten"
    double_zero = "double_zero"
    semolina = "semolina"


class YeastType(Enum):
    active_dry = "active-dry"
    instant = "instant"
    fresh = "fresh"
    sourdough_starter = "sourdough-starter"  # includes poolish


class FatType(Enum):
    evoo = "extra-virgin olive oil"
    butter = "butter"
    lard = "lard"
    vegetable_oil = "vegetable oil"


class SugarType(Enum):
    white = "white"
    brown = "brown"
    honey = "honey"


class Style(Enum):
    new_york = "new-york"
    neapolitan = "neapolitan"
    sicilian = "sicilian"


@dataclass(kw_only=True)
class Recipe:
    flour: float = 100.0  # baker's percentage basis: flour is always 100%
    flour_type: FlourType
    water: float
    salt: float
    yeast: float
    yeast_type: YeastType
    fat: float
    fat_type: FatType
    sugar: float
    sugar_type: SugarType
    style: Style
    source: str
    recipe_id: str
