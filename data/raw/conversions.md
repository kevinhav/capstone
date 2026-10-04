# Conversions needed for raw → curated intake

Derived from reviewing `neopolitan_style_recipes.md` and `sicillian_recipes.md` against
`pizza_style_template.csv`'s schema. Grouped by conversion type; each has concrete examples
pulled from the raw text and, where the raw data is ambiguous, a proposed convention rather
than just a formula. These conventions should be locked in before the intake notebook is
written, so every recipe is parsed the same way.

## 1. Volume → weight

Only needed when a recipe gives volume with no gram weight alongside it. When both are given
(common in these files), always take the stated gram weight — never re-derive it from the
volume, since stated conversions vary by source and re-deriving would silently disagree with
the author.

Cases with volume only, no grams given:
- Yeast: `1/8 teaspoon instant yeast` (KA Neapolitan), `2 teaspoons instant yeast` (KA
  Sicilian), `1 teaspoon instant yeast` (Caputo). Need an instant-yeast g/tsp constant.
- Salt: `2 ¼ teaspoons salt` (ATK Sicilian) — no weight given, no salt type specified either
  (see §7). Need a table-salt g/tsp constant as the default when type is unstated.
- Oil: `3 tablespoons extra-virgin olive oil` (ATK Sicilian). Water's 1g/mL shortcut does
  **not** apply — need an olive-oil density constant (~0.91 g/mL), not "1 tbsp ≈ 1 tbsp water."

Constants needed: instant yeast g/tsp, active-dry yeast g/tsp, table salt g/tsp, kosher salt
g/tsp (see §7 — brand-dependent), olive oil g/mL, water g/mL (=1, trivial).

## 2. Mass unit conversions (oz, lb, kg → g)

Straightforward `× 28.3495` / `× 453.592` / `× 1000`, but flag because one recipe is entirely
in ounces with no grams anywhere:

- Gozney Sicilian: `39.2 Oz "00" flour`, `19.5 Oz high gluten flour`, `1.76 Oz salt`,
  `0.6 Oz compressed yeast / 0.17 Oz instant yeast`, `1.44 Oz sugar`, `1.4 fl Oz olive oil`,
  `33.8 fl Oz water` — note **mass oz** (flour, salt, yeast, sugar) vs **fluid oz** (oil, water)
  are different conversions and this recipe uses both; the intake step needs to key off
  ingredient, not just see "oz" and apply one factor.

## 3. Baker's-percentage-only recipes → absolute grams

Several recipes give no absolute anchor at all, only percentages of flour:

- Modernist Cuisine: `100% flour, 62% water, 2% honey, 2% salt, 0.5% yeast, 0.5% vital wheat
  gluten` — zero grams anywhere.
- pizzamaking msg=165691: `Flour (100%), Water (59%), Salt (2.8%), Fresh Yeast (.17%)` — same.
- pizzamaking msg=202047: `~1.3kg flour` is given as "my typical batch," i.e. an approximate
  anchor, not a firm one.

**Convention needed:** since `flour_g` is a required absolute field but the downstream feature
pipeline (Phase 2) only uses baker's percentages anyway, pick a fixed reference batch size
(e.g. `flour_g = 1000`) for percentage-only recipes and derive the rest from that. Document
this in `notes` (e.g. "no absolute anchor given; normalized to 1000g flour") so it's not
mistaken for a real batch size later.

msg=86983 and msg=87025 already give both percentages and grams — no conversion decision
needed there, just parsing the table layout.

## 4. Ranges → point estimates

No recipe in these files gives ranges for every field, but several give a range for one field
where a point value is needed for the CSV:

- pizzanapoletana.org: `Salt: 40-60 grams`, `Fresh beer yeast 0.1-3 grams`, `Mother Yeast 5-20%
  of flour`, `Flour: 1,600/1,800`.
- pizzamaking msg=202047 headnote: `62.5% Water ... (play with this over time in a range of
  60-64%)`, `Salt ... not lower than 2.5% or more than maybe 3.1%`.

**Convention needed:** prefer the recipe's own headline/primary value when one is stated
alongside the range (msg=202047 gives both — use the headline `62.5%`/`3.0%`, not the range).
When only a bare range exists (pizzanapoletana.org), take the midpoint and record the full
range in `notes`.

## 5. Yeast-type equivalence (fresh / ADY / IDY / compressed)

The raw text itself supplies several explicit conversion ratios, which should be captured as
constants rather than re-derived each time:

- pizzanapoletana.org: `Dry yeast 1/3 of fresh yeast used (1g dry for 3g fresh)` → fresh:IDY
  ≈ 3:1.
- thepizzaheaven: `1g fresh yeast (0.1%) or 0.28g active dry yeast (0.03%)` → fresh:ADY ≈
  3.57:1.
- Gozney Sicilian: `0.6 Oz compressed yeast (1%) / 0.17 Oz instant yeast` → compressed:IDY ≈
  3.5:1, consistent with the standard ADY = IDY × 1.25 conversion.

Per `PROJECT_PLAN.md` Phase 2, normalization to an instant-yeast-equivalent happens downstream
in the feature pipeline, not at intake — so the raw CSV should keep whatever `yeast_type` and
`commercial_yeast_g` the source actually stated. Listing these ratios here so Phase 2 doesn't
have to re-derive them from scratch, and flagging that this file's recipes are one place they
came from (with citable sources).

## 6. Sourdough / preferment / poolish mass-balance

The template's own placeholder row notes a "mass-balance convention" for folding starter
flour/water into the totals — these raw recipes are the concrete cases that convention has to
handle:

- pizzamaking msg=202047: `1.3% Ischia Culture (fully active)` — no starter hydration % given;
  the source explicitly says "the hydration and flour you use in your culture don't matter
  much at quantities this low." Need a default assumed starter hydration (100% is the common
  baker's default) for cases like this where it's genuinely not specified.
- pizzanapoletana.org: `Mother Yeast 5-20% of flour used` — same missing-hydration issue.
- Gozney Neapolitan: a poolish (`125g water / 125g flour / 1.25g yeast / 1.25g honey`) is made,
  then only `240g preferment` of it is folded into the final dough. The poolish as mixed
  totals 252.5g, so the 240g used is a ~95% fraction — that fraction needs to be applied to
  pull the *proportional* flour/water/yeast contribution into the main dough's totals, not the
  full poolish batch.
- Gozney Sicilian: `Inoculated water - 165g preferment (10%) mixed with 160g water` — same
  fold-in treatment, and its own composition (is the 165g preferment itself flour+water+yeast,
  or something else) needs to be pinned down from the source before it can be converted.

## 7. Flour and salt sub-type conversions (brand/type-dependent constants)

- Salt density varies by brand enough to matter when only a volume is given: table salt,
  Diamond Crystal kosher, and Morton's kosher have meaningfully different g/tsp. msg=218034
  Part 2 explicitly switches to "Morton's Kosher Salt (1.924%)" mid-series where Parts 1/3 use
  a plain, unnamed higher percentage — this is the salt-type substitution changing the %, not
  a typo, and the intake step needs to preserve which salt type produced which number rather
  than averaging them.
- Flour blends don't fit the schema's single `flour_g`/`flour_type`/`flour_protein_pct` triplet:
  - msg=86983: 40% Semola / 60% Bread Flour, both weight and % given.
  - Gozney Sicilian: `"00" flour` + `high gluten/bread flour (32%)`.
  - ATK Sicilian: `319g AP flour` + `340g semolina flour`.

  **Convention needed:** sum to one `flour_g` total, compute a weight-weighted average
  `flour_protein_pct`, and record the actual blend composition in `notes` (e.g. "40% semola /
  60% bread flour") since the schema can't carry two flour rows per recipe.

## 8. Non-schema ingredients → notes, not fields

Per `PROJECT_PLAN.md`, sugar and process fields were deliberately cut from the schema. Several
raw recipes include ingredients with no home in the current columns at all:

- Sugar: KA Neapolitan, Gozney Sicilian (2.3%), ATK Sicilian, msg=405611 (1.0%).
- Honey: Modernist Cuisine (2%), Gozney poolish (1.25g).
- Vital wheat gluten: Modernist Cuisine (0.5%).
- Dough conditioner: msg=405611's `L-DMP 2.0%`.
- Proprietary additive: KA Sicilian's `King Arthur Pizza Dough Flavor (8g)`.

**Convention needed:** record these in `notes` for context (they may matter for qualitative
review) but exclude them from modeled fields — don't fold sugar into `fat_g` or invent a
column. Apply this consistently rather than deciding per-recipe.

## 9. Non-formula percentages that must be stripped before deriving ratios

msg=218034 Part 3 includes a `2% bowl residue compensation` baked into its "Total %." That
inflates the stated total beyond the true ingredient-percentage sum and would corrupt
hydration/salt/yeast % if taken at face value — needs to be identified and excluded before
computing baker's percentages, not treated as an ingredient.

## 10. Multiple leavening options presented as one recipe

pizzanapoletana.org and thepizzaheaven each present a single dough with alternate yeast
choices (fresh vs. dry, or fresh vs. mother yeast) rather than one committed formula.
**Convention needed:** pick the source's primary/first-listed option as the canonical row
(fresh yeast, typically), and note the alternate(s) in `notes` — rather than creating multiple
derived rows from one source, which would double-count a single recipe in the curated corpus.

## Open question (not a conversion, flagging while here)

`ny_style_recipes.md` is currently empty, but several formulas in `sicillian_recipes.md`
(msg=405611, msg=218034 parts 1-3, msg=86983) read as pizzamaking.com NY-style/Lehmann
formulas rather than Sicilian ones — worth a pass to confirm file placement before these get
parsed into `style_label` values, since that's a classification label the model depends on
directly.
