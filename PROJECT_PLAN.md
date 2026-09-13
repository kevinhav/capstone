# Project Plan

Companion to `proposal.md`. `revised_proposal.md` reframed the project as a representation/classification/optimization study rather than a recipe-generation tool, and validated the schema and centroid-based approach already built this session almost field-for-field. A follow-up round of feedback (appended to `revised_proposal.md`) then addressed what happens if curation lands closer to ~10 recipes per style than the 15-20+ floor originally hoped for — that feedback reshapes several pieces of this plan and is the basis for the methodology below. This document scopes the whole thing to what's achievable solo in ~3 months, pizza-only, with no live expert review panel, and is explicit about where the scoping weakens the academic claims so the final write-up doesn't overstate them.

## Scope decisions locked in this session

- **Timeline:** ~3 months.
- **Domain:** Pizza only. General bread styles are dropped from scope (`bread_style_template.csv` removed).
- **"Expert" ground truth:** No live review panel. Curated recipes are labeled via pizzamaking.com contributor consensus and published expert formulas (King Arthur, Forkish, López-Alt) — this is the corpus's *only* source of "expert" signal, so "agreement with expert judgment" (revised_proposal.md §5, §8) reduces to cross-validated consistency against these labels plus your own qualitative review, not an independent before/after panel study. **State this plainly as a limitation in the final write-up.**
- **Pilot framing, not universal classifier:** per the small-N feedback, this is explicitly a small-data, domain-informed pilot study on a deliberately small number of well-defined styles — not an attempt at broad regional-style coverage. The research question is "*can a low-dimensional, domain-informed representation distinguish a few well-defined pizza dough styles well enough to support useful recipe-adjustment recommendations?*", not "how many styles can we cover."
- **Class selection is curation-driven, not fixed in advance:** target whichever ~3 styles reach a curated-N floor (aim for ≥10) first — likely New York, Neapolitan, and one of Detroit/Chicago/Sicilian depending on what's actually findable. Those 3 are the primary evaluated set. Any additional style that doesn't clear the floor is demoted to affinity-score-only (shown in the tool, not included in the accuracy/CV evaluation) — this is stated explicitly rather than papered over.
- **Comparative modeling:** Lean, not the full 6-method sweep in §4 — centroid/affinity baseline plus one learned model (k-NN). Both use the *same* small, weighted feature set (see below) — k-NN doesn't escape the dimensionality problem just by being "learned."
- **Constrained optimization (§6-7):** Rule-based constraint layer, not a solver. revised_proposal.md explicitly allows this ("deterministic domain-knowledge adjustments... that's completely fine").

## Statistical approach to a small (~10/class) curated corpus

This is the direct response to the small-sample feedback and governs Phases 2-4 below.

1. **Dimensionality is the bigger risk than N itself.** ~10 examples/class cannot support a covariance structure across 15-30 candidate features (already true even before the "~10" number came up — full Mahalanobis was off the table at 15-20/class too). **Decided (2026-09-13):** the curated schema itself was cut down to just five ingredient categories — flour (+ type/protein%), water, salt, yeast (commercial or sourdough-starter, mass-balanced), and fat (oil/lard/etc., + type) — dropping sugar and *all* process/physical fields (fermentation schedule, oven type/temp, bake time, pan/thickness-factor) from the template entirely, not just from the model. This yields a 5-number core feature vector (hydration%, salt%, yeast-equivalent%, fat%, flour protein%) with **domain-assigned relative weights**, not learned or sample-estimated ones. Baking literature is fairly consistent that hydration and yeast/fermentation intensity are the primary discriminators between these styles, with salt and fat secondary — that ordering, not a data-driven feature-importance pass, sets the initial weights. Plain Euclidean distance across unweighted, differently-scaled features is *not* used.
   - **Tradeoff, stated plainly:** this trades away revised_proposal.md §2's process-representation question (does adding fermentation/bake/oven data improve stylistic similarity beyond composition alone?) for v1 — the raw curated CSV no longer even records those fields, so answering that question later requires re-curating, not just re-analyzing. Chosen deliberately to unblock Phase 1's curation bottleneck (fewer fields to look up per recipe) rather than left as an oversight.
2. **Centroid = prior + evidence, explicitly.** Formalizes what was already the plan: `estimated centroid = shrinkage combination of (expert-formula prior) and (curated-set sample mean)`, not a pure sample mean. Doesn't require a full Bayesian implementation — a simple fixed or N-dependent shrinkage weight toward the literature prior is enough, and is more defensible than treating 10 recipes as a precisely-estimated population centroid.
3. **Bootstrap is for uncertainty, not for manufacturing sample size.** Resampling 10 recipes 1,000 times does not produce the statistical information of 1,000 independent recipes — every resample is still built from the same 10 observations. What bootstrap *is* good for here: resample the curated set, recompute centroid/tolerance and score a held-out recipe each time, and report the resulting spread (e.g. "New York 72% ± 8%, Neapolitan 21% ± 7%") instead of a bare point estimate. Also useful for an influence check — does the classification depend heavily on one particular recipe in the corpus? That's worth knowing regardless of the modeling approach.
4. **Feature-level augmentation is for testing pipeline mechanics only.** Scaling a recipe, converting units, or perturbing parameters within literature-justified ranges produces legitimate recipe *variants*, but not independent observations — they're useful for checking the pipeline behaves sensibly (e.g. does scaling a recipe 2x still land in the same place in feature space) and are never used to claim a larger effective N. **Leakage guardrail:** if any augmented/bootstrap variant of a recipe is ever used near an evaluation step, all variants of that recipe stay entirely within whichever split (train or test) the original recipe was assigned to — never split across both.
5. **Evaluation is repeated stratified train/test splits + bootstrap uncertainty, not a single leave-one-out pass.** For the ~3-class pilot set: repeated stratified splits (e.g. 7 train / 3 test per class, repeated over many random splits), centroid/tolerance re-established from each training split, held-out recipes classified, accuracy and confusion matrix recorded per split. Report the *distribution* of results across splits, not one number — "X% accuracy under repeated stratified cross-validation, with substantial uncertainty given the small curated dataset," plus the confusion matrix. No single metric gets reported without its uncertainty.

## Research questions this plan answers

Mapped from revised_proposal.md's "what makes this graduate-level" framing (§ = its section numbers), reframed around the small-N feedback:

1. **Representation** (§2) — does a small, domain-weighted baker's-percentage + process feature vector capture stylistic difference at all?
2. **Classification** (§3-4) — does a centroid/affinity baseline separate a few well-defined styles under repeated stratified CV, and how does k-NN compare on the same feature set? (Not: does one "beat" the other — a null result is a legitimate finding at this N.)
3. **Similarity** (§5, scoped) — does the model's notion of affinity track the pizzamaking.com-consensus labels, with what uncertainty (via bootstrap), and does it hold up under your own spot-check?
4. **Optimization** (§6) — does a target-directed delta recommendation actually move a held-out recipe's feature vector closer to the target centroid?
5. **Constraints** (§7) — do rule-based constraints produce a *feasible* recommendation (not just a mathematically-closer one) given stated equipment/ingredient limits?

The core academic contribution is the representation + domain-informed distance model + honest uncertainty quantification on a deliberately small pilot corpus — not competing with a conventional ML classifier on sample size.

## Phases

### Phase 1 — Corpus curation (weeks 1-3)
- Populate `data/curated/raw_intake.md` from pizzamaking.com threads and the three expert sources. Target ≥10 per style, but prioritize depth on whichever 3 styles are actually reaching that floor over breadth across 5-6 — per the pilot framing above, a well-supported 3-class study beats a thin 5-6 class one.
- Parse raw entries into `pizza_style_template.csv` (raw grams + starter fields, per the schema already agreed).
- **Deliverable:** populated CSV, with `source`/`source_type` filled in for every row, and an early read on which 3 styles will form the primary evaluated set.

### Phase 2 — Feature pipeline (weeks 3-5, overlaps Phase 1)
- Notebook: `01_feature_pipeline.ipynb`.
- Implement: sourdough mass-balance conversion (fold `starter_g`/`starter_hydration_pct` into effective flour/water), baker's-percentage derivation (hydration%, salt%, fat%), flour-protein lookup table (fills `flour_protein_pct` when not directly stated, keyed off `flour_type`), yeast-type normalization to instant-equivalent (commercial + the approximate sourdough leavening heuristic, flagged via `leavening_source`).
- Feature selection is already done (see above) — this phase just computes the 5 resulting numbers and attaches the domain weights, it doesn't need to discover the feature set.
- **Mechanics sanity check (optional, not evaluation):** generate a few scaled/unit-converted variants of curated recipes and confirm the pipeline places them where expected in feature space. Labeled clearly as a pipeline test, never counted toward corpus size.
- **Deliverable:** `data/processed/pizza_features.csv` (5-column weighted feature set: hydration%, salt%, yeast-equivalent%, fat%, flour protein%) + the notebook that produces it, reproducibly, from the raw CSV.

### Phase 3 — Deterministic baseline (weeks 5-6)
- Notebook: `02_baseline_centroid.ipynb`.
- Centroid per style as a shrinkage combination of the literature-formula prior and the curated-set sample mean; weighted distance (domain-assigned weights from Phase 2, not full covariance) converted into an **affinity score** — explicitly not a calibrated probability.
- Evaluate via repeated stratified train/test splits (not simple leave-one-out) on the 3-style primary set; bootstrap the curated set to attach an uncertainty band to each affinity score and to run an influence check (does the result hinge on one recipe?).
- **Deliverable:** working affinity-scoring function + a repeated-CV accuracy distribution/confusion matrix + bootstrap uncertainty bands. This is the must-ship core of the whole project — everything after this phase is comparison and extension.

### Phase 4 — Lean comparative model (weeks 6-7)
- Notebook: `03_knn_comparison.ipynb`.
- Fit k-NN (small k) on the *same* reduced, weighted feature set from Phase 2 — k-NN faces the same dimensionality ceiling as the baseline, so it doesn't get a richer feature set "for free."
- Same repeated-stratified-CV + bootstrap methodology as Phase 3, so the comparison is apples-to-apples.
- Expected and acceptable outcome either way: if k-NN doesn't beat the baseline, that's a legitimate, reportable finding given the sample size — frame it that way going in, don't chase a win.
- **Deliverable:** side-by-side accuracy-distribution comparison + written discussion.

### Phase 5 — Constraint-aware recommendation (weeks 7-9)
- Notebook: `04_recommendation_engine.ipynb`.
- Predictive half: per-feature delta vector from a recipe to a target style's centroid (already designed).
- Constraint half, kept architecturally separate per revised_proposal.md §7: since the model's recommendation delta only covers the 5 composition features (it can't recommend "raise your oven temperature" — oven isn't a model dimension), equipment/environment constraints (oven max temp/type, available fermentation time, flour actually on hand) act as a **feasibility gate on style selection** rather than something the delta adjusts — e.g. flag that Neapolitan's characteristic char/spring isn't achievable in a home oven regardless of composition, and suggest NY or Grandma as reachable alternatives instead.
- **Deliverable:** given (recipe, target style, constraints) → feasible recommended changes.

### Phase 6 — Recommendation validation (weeks 9-10)
- Since there's no live panel, validate two ways: (a) apply the recommended delta to a held-out recipe and confirm its affinity to the target style increases (a self-consistent, referee-free check); (b) your own qualitative pass over a sample of before/after pairs, scored informally.
- **Deliverable:** validation notebook + a short written note on where the self-consistency check and your own judgment diverge, if they do — that divergence is itself worth reporting.

### Phase 7 — Tool + write-up (weeks 10-13)
- Minimal interface (CLI or a simple notebook widget/artifact is fine — polish is not the point) wrapping Phases 3-5 into: input a recipe → get affinity distribution with uncertainty → pick a target → get a feasible recommendation.
- Final report tying each phase back to its research question above, with limitations called out explicitly: no live panel, deliberately small 3-style pilot corpus, literature-sourced centroids from a handful of authors, sourdough leavening-equivalent is a flagged approximation, and any style that didn't clear the curation floor is shown as affinity-only with that caveat stated.

## Immediate next action

Phase 1 is still the bottleneck, but the target has changed: stop optimizing for breadth (5-6 styles) and instead push for depth on whichever 3 styles are actually accumulating recipes fastest. That 3-style pilot, done honestly with uncertainty reported, is the whole plan now — not a fallback.
