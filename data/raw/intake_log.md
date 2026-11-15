# Intake log — first population pass

Populated `data/pizza_style_template.json` from `neopolitan_style_recipes.md`,
`sicillian_recipes.md`, and `ny_style_recipes.md`, using `Conversions` and the enums in
`recipe.py`. Per-field provenance (raw snippet, conversion method, exceptional notes) is
recorded on each record's own `mapping` section — this log covers the recipe-level and
policy-level decisions that don't belong to one field.

**Result:** 32 recipes populated (11 neapolitan, 12 new-york, 9 sicilian), 2 skipped.

## Update — resolved open questions from the first pass

- **`FatType.vegetable_oil` added.** The 5 flagged NY recipes (soybean oil, vegetable oil, or
  unqualified "oil") now use it instead of the `evoo` placeholder. "Soybean Oil" and
  "vegetable oil" matched the new alias directly; bare, unqualified "Oil" (3 recipes) still
  required a manual default, now to `vegetable_oil` rather than `evoo` (a neutral oil is the
  more standard convention in American-style pizza dough than olive oil when unstated).
- **`FlourType.semolina` added.** Unblocked `sicilian_010` (ATK Sicilian), where semolina
  (340g) is the dominant flour over all-purpose (319g).
- **`new_york_010`'s discrete-IDY-only treatment confirmed** — no change made.
- **`sicilian_009` (Gozney Sicilian) re-added, corrected per your guidance:** the 165g
  "inoculated water" preferment's own composition wasn't stated, so it's now split 50/50
  flour:water (`split_starter(165, hydration_pct=100)` — the same default-hydration
  convention already used for other unstated-composition preferments), then folded into the
  main flour/water totals along with the additional 160g cold water it's mixed with. Result:
  `water=71.11%, salt=2.86%, yeast=0.97% (fresh), fat=2.16% (evoo), sugar=2.34% (white)`,
  `flour_type=double_zero` (dominant between the "00" and high-gluten/bread flour blend).

## Style labels

Per instruction, every recipe's `style` matches the `.md` file it came from, regardless of
how the formula itself reads. Flagging again for the record: `sicilian_001` through
`sicilian_004` (msg=405611, msg=218034 parts 1-3) read as NY-style/Lehmann formulas
(high-gluten flour, 62-71% hydration, IDY, no lard/semolina/pan-oil treatment) rather than
Sicilian ones. Kept as `sicilian` since that's the file they're in.

## Standing conventions applied (not asked per-instance)

- **Unspecified flour type** → defaulted to the style-conventional flour: `double_zero` for
  neapolitan, `high-gluten` for new-york, `bread` for sicilian.
- **Unspecified yeast type** (bare "yeast," no qualifier) → defaulted to `instant`.
- **Multiple ingredient/leavening options in one recipe** (e.g. "fresh yeast or active dry
  yeast," three alternate leavening methods in the AVPN formula) → took the first-listed
  option; alternates noted in that field's `mapping.note`.
- **Ranges** → took the source's own headline value when one was given alongside a range
  (e.g. msg=202047's "62.5%... range of 60-64%" → used 62.5); otherwise took the range's
  midpoint (e.g. AVPN's "40-60 grams salt" → used 50g).
- **Yeasted preferment/poolish with known flour+water** → folded directly into the main
  dough's flour/water totals, scaled by the used-fraction when only part of a larger batch
  is added (Gozney Neapolitan: only 240g of a 252.5g poolish is used, so poolish
  contributions were scaled by 240/252.5 before folding in).
- **Preferment/starter with unstated hydration** → assumed 100% (`DEFAULT_STARTER_HYDRATION_PCT`)
  via `split_starter`.
- **Sourdough starter dosage** (Ischia Culture, Mother Yeast — described as "X% of flour,"
  not as a discrete preferment with its own flour+water) → recorded as-stated under
  `yeast_type=sourdough_starter`, *not* mass-balanced into flour/water. This is a different
  treatment than the poolish case above: a poolish is literally flour+water folded into the
  dough, while a starter dosage is the leavening rate itself.
- **Non-schema ingredients** (vital wheat gluten, L-DMP dough conditioner, King Arthur Pizza
  Dough Flavor, semolina used only for bench-dusting) → excluded from modeled fields,
  preserved verbatim in `raw_text` only.
- **Bowl residue compensation** (msg=218034 Part 3's stated 2%) → confirmed it doesn't change
  the ingredient ratios (Part 3's per-ingredient percentages are identical to Part 1's), so no
  correction was applied.

## Conversions.py additions made during this pass

- `INGREDIENT_DENSITY_G_PER_ML["sugar_white"]` / `["sugar_brown"]` — no sugar density existed
  before; needed for volume-measured sugar (e.g. KA Neapolitan's "1/2 teaspoon granulated
  sugar").
- `FLOUR_DENSITY_G_PER_CUP` (by `FlourType`) — no flour density existed before; needed for
  one recipe (msg=31163) given entirely in cups with no gram weight anywhere.

## Skipped (2)

- **sicilian_006** (msg=87025, lard/Strutto formula) — no yeast line anywhere in the excerpt;
  yeast has no safe default the way flour type does. Still open — needs the original forum
  post's full formula.
- **new_york_002** (msg=49940) — author explicitly states the flour amount is "approximate...
  varies with humidity, season, temp," not a fixed measurement. Not a schema gap, so nothing
  to add here — genuinely not reducible to a point estimate.

## Second population pass (2026-11-14)

Source: `data/raw/raw_intake.md` RAW-001 through RAW-010. Converted with the `capstone.data`
helpers under the standing conventions above; per-field provenance is on each record's
`mapping`. **Result:** 9 recipes added (32 -> 41: 17 new-york, 12 neapolitan, 12 sicilian),
1 skipped. All 9 validated against `pizza_recipe.schema.json`.

| RAW id | recipe_id | Source |
|---|---|---|
| RAW-001 | new_york_013 | Peter Reinhart, Pizza Quest NY-style dough |
| RAW-002 | new_york_014 | King Arthur NY-style pizza class workbook |
| RAW-003 | new_york_015 | Ooni New York-Style Pizza |
| RAW-004 | new_york_016 | Gozney New York Style Pizza Dough (Luis Perez) |
| RAW-005 | new_york_017 | Caputo, Mimmo's New York Style Pizza |
| RAW-006 | sicilian_011 | Caputo Sheet Pan Pizza Dough |
| RAW-007 | sicilian_012 | Ooni Sicilian Pizza |
| RAW-008 | sicilian_013 | Ooni NEPA Pan-Fried Sicilian (Jim Mirabelli) |
| RAW-009 | neapolitan_012 | America's Test Kitchen Neapolitan-Style Pizza |

Decisions specific to this pass:

- **Style labels for sicilian_011 and sicilian_013 confirmed.** The Caputo page is titled
  "Sheet Pan Pizza Dough" but its headnote and method call it Sicilian-style; the NEPA recipe
  is a Northeastern Pennsylvania regional variant that labels itself Sicilian-style.
- **King Arthur NY web recipe not added separately.** Same formula as the RAW-002 workbook.
- **new_york_013 (Reinhart):** used the source's parenthetical ounce weights throughout,
  including water (14 oz) and oil (1.5 oz), rather than converting the volume measures.
- **new_york_016 (Gozney):** the 150g poolish is split 50/50 via `split_starter`, which
  reproduces the source's own stated totals (1075g flour, 665g water) exactly. The source
  prints oil as ".7%"; used the 40g gram weight (3.72%), which matches its imperial listing.
- **new_york_017 (Caputo NY):** ingredient list says "Active Yeast", method says "Instant
  Yeast"; recorded active-dry per the ingredient list.
- **neapolitan_012 (ATK):** the cooked flour paste (16g flour, 79g water) is folded into the
  totals, giving ~76% hydration. High for the style but as published.
- **sicilian_013 (NEPA):** the 30g peanut oil greases the pan for frying and is excluded.
- **Fine sea salt measured by volume** (sicilian_012) uses the table-salt density.

## Skipped in this pass (1)

- **RAW-010** (Ooni Neo-Neapolitan, Cody Splane) — leavened with a 131g sourdough starter on
  654g flour, a ~20% starter dosage that isn't comparable to the commercial-yeast percentages
  in the yeast feature; also labeled "neo-Neapolitan" (bread + whole wheat flour, olive oil),
  a borderline fit for the style.
