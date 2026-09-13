# Ideas

## North Star (not in scope for capstone itself)

- Long-term direction beyond the capstone: an advanced music discovery/artist-recommendation engine — going beyond audio-fingerprint/genre-playlist approaches toward genuine discovery via emotion, lyrical prose, and instrumentation.
- Capstone should be chosen/architected as a building block toward this, not just a standalone exercise. See note under Multimodal Genre Ambiguity.

## Music

### Multimodal Genre Ambiguity (Audio + Lyrics Fusion)

- Train separate audio-only and lyrics-only classifiers over a small taxonomy (~6-8 genres), each outputting a probability distribution over genres.
- Blend the two distributions; focus the analysis on *disagreement* between modalities (e.g. lyrics read as country, audio reads as trap) rather than chasing top-1 accuracy.
- Data: FMA (Free Music Archive) for actual audio clips + genre labels, joined to a lyrics dataset (e.g. Genius/Kaggle) by artist/title.
- Scoped down from original idea (raw audio + lyrics + full distributional genre modeling) to fit 3 months without needing hard-to-source paired metadata.
- Narrative/contribution is the fusion + disagreement analysis, not classification accuracy — needs framing buy-in from committee.
- Building-block note: if the per-modality models are designed to output embeddings (not just class probabilities), this becomes reusable infrastructure for the North Star discovery engine — nearest-neighbor search over blended embedding space instead of genre classification. Chord progression (see below) is a natural third modality to add later for instrumentation signal; lyric sentiment/emotion tagging could be seeded alongside genre in the lyrics model without expanding capstone scope now.

### Genre Classifier (original, likely out of scope)

- Sound files + lyrics + present output as a blended probability distribution across genres.
- Blocked by: limited access to paired audio/lyrics/metadata at scale, and 3-month timeline.

### Chord Progression Prediction (structural baseline vs. learned model)

- Predict next-chord / chord progressions. Data is tractable and rich: HookTheory TheoryTab (labeled by song/genre/section) and McGill Billboard corpus — most data-rich idea of the bunch, no scraping/labeling needed.
- Risk: next-chord prediction via LSTM/transformer alone is well-trodden academic territory — not novel by itself.
- Framing: build a Markov chain / transition-graph model as an interpretable baseline (nodes = chords, edges = transition probabilities; compare graph topology across genres, e.g. jazz vs. pop chord networks). Train a small transformer alongside it and analyze what longer-range structure it captures that the graph/Markov model can't (functional harmony, cadence anticipation).
- Echoes the disagreement/comparative-analysis framing from the multimodal genre fusion idea (simple structural model vs. learned model, not just accuracy).
- Open question (2026-08-31): still feels underdeveloped — missing a clear "so what"/application layer that the other ideas have (finance tool, forecasting tool, generative dough tweaker). Candidate directions to flesh out: (a) tie into the genre-fusion idea as a third modality (chord progression as another signal blended into the genre distribution), or (b) a generative/interactive angle — given a progression, suggest next chords shifted toward a target genre/style, mirroring the bread dough "push toward style X" framing.

### Genre Recommendation System

- Identify key attributes of 

## Structured Data Extraction from Excel

### Messy Spreadsheet Table Extraction (ML boundary detection + LLM agent)

- ML model detects table boundaries in real-world Excel sheets (merged cells, multi-row headers, nested sub-tables), then an LLM agent uses tools to extract and structure the data.
- Practical/finance-relevant, but risk of reading as "just a tool" rather than a research contribution.
- Reframe for novelty: build + open-source a labeled benchmark of messy real-world spreadsheets, since most public table-extraction benchmarks use clean/well-formed tables. Contribution = harder, realistic benchmark + evaluation of where boundary-detection/LLM extraction fails, not just the pipeline.
- Data source: Enron email/spreadsheet corpus — easy source of messy, human-created real-world spreadsheets, solves the data acquisition problem.
- Still need to hand-label a ground-truth eval set from the sourced sheets; this is the main time cost in a 3-month window.

## Bread Baking Recipe Style-Space

### Learned Style-Space for Bread Dough Formulation

- Generalized from a pizza-only idea into bread baking broadly (pizza, sourdough, focaccia, ciabatta, baguette), since these all share the baker's-percentage convention (ratios relative to flour weight: hydration, salt, yeast, fermentation time/temp) — one consistent structured numeric feature space across styles.
- Deliberately excludes cakes/pastries/cookies — their ratio logic (fat/sugar/leavening) isn't baker's-percentage-based, and including them would reintroduce a heterogeneous-taxonomy problem.
- Two components: (1) classify a recipe's style from its ratios, (2) the more novel piece — given a recipe and a target style, learn a mapping/optimization that suggests directed coefficient tweaks (e.g. "push toward Neapolitan" → raise hydration, lower yeast %, extend fermentation). A controllable-generation/recommender problem in a small interpretable space.
- Image classification (photo → style) is a viable stretch goal but shouldn't be the spine — it's commodity transfer-learning work, not a novel contribution.
- Data source status (2026-09-05): RecipeDB's public API (foodoscope.com) turned out to be blocked — its `includeDietrxCategories` filter is a diet-type taxonomy (vegan/pescetarian/etc.), not a food-category filter, and the actual `Bakery` category enum returns zero recipes even through the vendor's own official playground. Confirmed as a gap/bug on Foodoscope's end, not fixable client-side. Pivoted to two alternatives:
  - **Recipe1M+** (im2recipe.csail.mit.edu) — access request submitted, pending approval. ~103K of its 1M+ recipes have fully parsed quantity+unit fields (same structured-ingredient advantage RecipeDB offered), at larger scale. Still need to filter down to bread/dough recipes once access is granted.
  - **RecipeKG** (github.com/IDIASLab/RecipeKG, `Data/Json-Data/recipes1`) — ~20K AllRecipes.com recipes as schema.org JSON-LD, available now with no approval wait. Has reliable native site categorization (`recipeCategory` breadcrumb, e.g. "Desserts > Cookies > Drop Cookie Recipes") to filter for bread/bakery — solves the category-filtering problem RecipeDB failed at. Tradeoff: `recipeIngredient` is raw free-text ("2⅔ cups packed brown sugar"), not pre-parsed — reintroduces ingredient parsing, but scoped to the narrow bread-family vocabulary (flour, water, yeast, salt, sugar, butter, eggs) a lightweight rule-based/regex parser should suffice, no need for a general NLP ingredient-phrase model. Apache-2.0 code license.
  - Working plan: use RecipeKG now (available immediately, category filter already solved) and fold in Recipe1M+ later for scale if/when access comes through.
- Precision caveat (still applies regardless of source): both are home-recipe-site quantities (rounded cups/tbsp), not baker-forum precision — expect noisy derived percentages. Supplement with a small hand-pulled set from pizzamaking.com/TheFreshLoaf formula threads (often already stated as percentages or exact grams) as a high-precision calibration/validation subset.
- Post-capstone data flywheel (not in scope for the 3-month build, but the plan going in): once the classifier + coefficient-tweak tool has real functionality, invite baking forum communities (pizzamaking.com, TheFreshLoaf, r/Bread, r/Sourdough) to submit their own recipes directly, growing a higher-precision, community-sourced dataset over time and building organic interest in the tool. Treat this as the roadmap/growth phase, not a capstone deliverable — the capstone ships on RecipeDB-derived data alone.
- Tradeoff: most tractable of the ideas so far (least data risk, least scope risk), but reads more whimsical — worth weighing against having at least one "serious"-reading candidate for the portfolio narrative.

## ESPV 2.0