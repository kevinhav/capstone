from capstone.recipe import FatType, FlourType, SugarType, YeastType


class Conversions:
    """Constants and text-to-enum mappings for turning raw recipe text into
    the canonical baker's-percentage Recipe format."""

    # -- absolute unit conversions --------------------------------------

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

    # for the rare source recipe that measures flour by volume with no
    # gram weight given at all
    FLOUR_DENSITY_G_PER_CUP: dict[FlourType, float] = {
        FlourType.all_purpose: 125.0,
        FlourType.bread: 127.0,
        FlourType.high_gluten: 130.0,
        FlourType.double_zero: 130.0,
        FlourType.semolina: 167.0,
    }

    # salt density varies enough by brand/grind to matter when only a
    # volume is given and no weight is stated alongside it
    SALT_DENSITY_G_PER_TSP: dict[str, float] = {
        "table": 6.0,
        "diamond_crystal_kosher": 2.8,
        "mortons_kosher": 4.8,
    }

    # -- yeast-type equivalence ------------------------------------------

    # multiplier to convert a gram amount of this yeast type into its
    # instant-dry-yeast equivalent (grams_instant = grams_x * ratio)
    YEAST_TO_INSTANT_RATIO: dict[YeastType, float] = {
        YeastType.instant: 1.0,
        YeastType.active_dry: 0.8,  # ADY = IDY * 1.25
        YeastType.fresh: 1 / 3,  # fresh = IDY * 3
        # sourdough_starter has no fixed ratio - handled via mass-balance, not scaling
    }

    # -- preferment handling ----------------------------------------------

    # poolish is defined as equal parts flour and water by weight; also used
    # as the default assumed hydration for a sourdough starter/culture whose
    # own hydration isn't stated in the source recipe
    DEFAULT_STARTER_HYDRATION_PCT: float = 100.0

    @staticmethod
    def split_starter(total_g: float, hydration_pct: float = DEFAULT_STARTER_HYDRATION_PCT) -> tuple[float, float]:
        """Split a preferment's (poolish, sourdough starter, etc.) total
        weight into its (flour_g, water_g) components, to be folded into the
        main dough's totals. hydration_pct is water as a percentage of
        flour, e.g. 100 for a poolish or an unstated-hydration starter."""
        flour_g = total_g / (1 + hydration_pct / 100)
        water_g = total_g - flour_g
        return flour_g, water_g

    # -- raw text -> canonical enum ---------------------------------------

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

    @staticmethod
    def match_alias[T](text: str, aliases: dict[str, T]) -> T | None:
        """Match raw ingredient text against an alias table, preferring the
        longest (most specific) matching key so e.g. "brown sugar" wins over
        the bare "sugar" fallback."""
        text = text.lower()
        for key in sorted(aliases, key=len, reverse=True):
            if key in text:
                return aliases[key]
        return None

    @staticmethod
    def to_grams(
        amount: float, unit: str, density_g_per_ml: float | None = None
    ) -> float:
        """Convert a mass or volume amount to grams. Volume units require
        density_g_per_ml (see INGREDIENT_DENSITY_G_PER_ML)."""
        if unit in Conversions.MASS_TO_GRAMS:
            return amount * Conversions.MASS_TO_GRAMS[unit]
        if unit in Conversions.VOLUME_TO_ML:
            if density_g_per_ml is None:
                raise ValueError(
                    f"density_g_per_ml required to convert volume unit '{unit}' to grams"
                )
            return amount * Conversions.VOLUME_TO_ML[unit] * density_g_per_ml
        raise ValueError(f"unrecognized unit: {unit}")

    @staticmethod
    def to_baker_percentage(ingredient_g: float, flour_g: float) -> float:
        """Express an ingredient's weight as a percentage of total flour weight."""
        return ingredient_g / flour_g * 100
