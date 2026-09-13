# Project Proposal

## Summary

Home bread and dough making has become a growing industry and area of interest for the consumer segment. Given the narrow focused set of ingredients, standard sets of techniques, and large array of possible outcomes, bread and dough recipes are well represented as formulas expressed as proportions of ingredients and parameterized techniques. This project will develop a recipe development tool intended for both home cooks and professionals to modify, develop, or adjust their bread and pizza dough recipes to achieve specified results. The project will curate a database of hand-selected, well-documented recipes, classify a user's recipe against specific subclasses such as "New York pizza dough" or "French baguette", and guide users to adjust their recipes towards a specific sub class.

## Industry Context

Since COVID-19, consumer baking interest has dramatically surged. In March 2020, King Arthur, a company known for producing high quality consumer and commercial flour products, reported a 2,000% year-over-year growth in online flour sales.[^ka-2000] Over the full year, King Arthur sold 156 million pounds of flour, up 58% year-over-year,[^ka-58] and the brand has since become the #1 branded family flour in the United States by both dollars and units.[^ka-number-one] Companies like Ooni and Gozney that produce specialized outdoor pizza ovens, mixers, and other consumer baking accessories have seen staggering growth over a similar period; Ooni in particular is reported to have seen +300% sales growth in 2020, which quadrupled again in 2021.[^ooni] Gozney's audited UK filings show four consecutive years of compounding growth, from £12.9M turnover in FY2021 to £60.7M in FY2024.[^gozney]

This trend has continued well into the last five years; Google searches for "sourdough" keywords have increased every year since an initial spike in 2020, and even becoming more specific, such as "sourghdough bagel" and "homemade sourdough bread".[^trends]

## Simple Ingredients, Complex Technique

Baking leavened and unleavened bread is an ancient art, but modern bakers and recipes are developed around a baker's proportions style of recipe. Due to the small list of typical ingredients, many modern recipes simply express themselves in terms of ratios with regards to the total flour used.

This gives us a very convenient way to write and scale recipes. It also gives us a way to consistently represent different bread recipes as vectors of ingredients and parameterized techniques.

Consider the two example recipes below for a baguette and Neopolitan Pizza Dough. The overlap in ingredients and technique is substantial, but we can see clear differences that make the end result so specific.

_Placeholder_


## Benefit

The aforementioned companies have enjoyed significant growth by solving recipe consistency via equipment solutions, however very little research has been devoted to the recipe consistency and development. Common issues include imprecise volume measurements which can drift up to 33% depending on scooping technique,[^flour-measure] variance in home oven thermostats (90 degree variance unit-to-unit),[^oven-variance] and effects of regional humidity, air pressure, and ingredient processing / availability.[^altitude]

The tool will benefit home cooks and professionals alike by allowing any "starting recipe" to be adjusted and scaled towards the user's target outcome. Instead of expensive and time-intensive trial and error, users will be able to simply adjust the recipe parameters to understand how it will affect the outcome of their product. The tool will encourage exploration and experimentation for experienced bakers, and a helpful guide and jumping-off point for novices to achieve good results. A parameterized approach also benefits a broad range of users with limited equipment, live in extreme areas of humidity, aridness, or altitude, or simply have less access to specialty ingredients.

The end goal of the tool is to enable a more data-informed approach to baking, as opposed to pure trial and error.


## Data Availability

Given the volume and variability of publicly available recipes, and an initial exploration of large-scale, publicly-scraped recipe data finding regional dough styles too sparsely and inconsistently named to support classification directly, this project will instead curate a small, hand-selected database of well-documented recipes per subclass, sourced from cookbooks, baking competitions, and baking-community formula threads (e.g. pizzamaking.com). Recipes will be logged via a lightweight raw-text intake process and parsed into a structured schema before normalization.

"Canoncial" recipes will be established from aggregated well-regarded sources, as to create as clear a definition of possible subclasses as possible. Because the curated set will be small relative to a scraped corpus, subclass definitions ("centroids") will be anchored in baker's-percentage formulas published by expert sources (King Arthur, Forkish, López-Alt, pizzamaking.com) rather than estimated purely from sample averages; the curated recipes establish the acceptable variation around each subclass rather than its location.

Recipes will be normalized into a standard format (baker's percentages: hydration, salt, yeast, and fat as a ratio of total flour weight) to allow for effective comparison. Where standard baking units are less precise (e.g. volume measurements), as constant conversion will be used. Sourdough-leavened recipes will be converted to the same commercial-yeast baseline via a mass-balance convention (splitting a starter into its flour/water contribution at its stated or assumed hydration), with leavening strength treated as an approximate, separately-flagged feature given the difficulty of establishing a mature starter's activity from text alone.

## Process

The entire modeling pipeline will be as follows;

- Recipe curation & intake: Recipes will be hand-selected from expert sources and logged in raw text form via a lightweight intake process, to be parsed into the project's structured schema.
- Normalization: Recipe ingredients and techniques will be normalized into a standard format, including a mass-balance conversion for sourdough-leavened recipes.
- Labeling: Each curated recipe will be labeled with its subclass (e.g. "New York pizza dough") and source provenance.
- Ingredient Encoding: Ingredients will be converted to weight-based proportions, the standardized "baker's percentages". This will account for both recipe scale and standardization.
- Feature Encoding: Given the small curated sample, the feature set is deliberately reduced to five ingredient-based ratios per recipe — hydration (water), salt, yeast (commercial or sourdough-starter equivalent), fat (oil, lard, etc.), and flour protein content — each weighted by domain judgement rather than learned or sample-estimated weights, with hydration and yeast/fermentation intensity treated as the primary discriminators per baking literature. Process and physical parameters (fermentation schedule, oven type and temperature, dough thickness factor) are deferred beyond this project's scope rather than included as a large, sparsely-supported feature vector.
- Centroid & Tolerance Estimation: For each subclass, a centroid will be established as a shrinkage combination of published expert formulas (prior) and the curated recipes' sample mean (evidence), with the curated recipes also used to estimate the acceptable variation (tolerance) around it.
- Distance Scoring: A new or adjusted recipe's feature vector will be scored against every subclass centroid and converted into a style **affinity score** (e.g. "60% New York, 40% Neapolitan"), explicitly interpreted as a similarity measure rather than a calibrated probability, with a bootstrap-derived uncertainty band attached to each score.
- Recipe Adjustment: A user interface will be developed allowing users to input a recipe. The tool will respond with the affinity distribution above, plus the per-feature difference to a chosen target subclass's centroid as a direct, directional recommendation.

## Scope & Limitations

- Classes will be limited to unenriched doughs and will be determined based on data availability.
- Scope is narrowed to pizza dough styles, since regional pizza styles are the most concretely named and best-documented in baking literature and community sources (e.g. pizzamaking.com). General bread styles are out of scope for this project. Candidate styles include New York, Neapolitan, Detroit, Chicago, and Sicilian, but this project is deliberately framed as a small-data pilot study on a handful of well-defined styles rather than an attempt at broad regional coverage: the primary evaluated set will be whichever ~3 styles reach a curated-sample floor first, with any style that doesn't clear that floor shown only as an affinity score, not included in formal evaluation.
- Recipes will be hand-picked exemplary formulas from expert sources including King Arthur, James Beard Award winner Ken Forkish, author of Flour Water Salt Yeast,[^forkish] James Beard Award winner Kenji López-Alt,[^kenji] and baking-community formula threads (e.g. pizzamaking.com), rather than aggregated from general recipe websites. The overall expertise behind these formulas will still vary by source, so each curated recipe records its provenance (cookbook, competition, forum consensus, etc.) for later weighting.
- Given the resulting small sample size per subclass (on the order of ten per style, not hundreds), subclass centroids will be anchored in the published formulas above rather than estimated purely from sample means, with the curated recipes establishing tolerance/variation around each centroid. At this sample size, evaluation uses repeated stratified train/test splits and bootstrap-based uncertainty estimates rather than a single reported accuracy figure, and results are reported with their uncertainty rather than as point estimates. Sourdough-leavened recipes carry an additional, explicitly-flagged approximation for converting starter activity into an equivalent leavening rate.

## Sources

[^ka-2000]: [King Arthur's Flour Sales Rise Over 2,000% in March (Adweek)](https://www.adweek.com/brand-marketing/king-arthur-flour-sales-up-over-2000-percent-march-coronavirus-baking/)
[^ka-58]: [King Arthur Baking Company Sees Flour Sales Rise 58% Amid Pandemic (Yahoo Finance)](https://finance.yahoo.com/news/king-arthur-baking-company-sees-flour-sales-rise-58-amid-pandemic-130854511.html); [Perishable News](https://perishablenews.com/bakery/king-arthur-baking-company-sees-flour-sales-rise-58-amid-pandemic/)
[^ka-number-one]: [Holding to Founding 1896 Principle Pays Dividends at King Arthur Baking (Baking Business)](https://www.bakingbusiness.com/articles/64760-holding-to-founding-1896-principle-pays-dividends-at-king-arthur-baking)
[^ooni]: [Ooni Pizza Oven: From Backyard Side Hustle to $200 Million (Entrepreneur)](https://www.entrepreneur.com/starting-a-business/ooni-pizza-oven-from-backyard-side-hustle-to-200-million/488828); [Ooni's Revenue Decreases by 24% but Financial Health Improves (CookOut News)](https://www.cookoutnews.com/oonis-revenue-decreases-by-24-but-financial-health-improves/)
[^gozney]: Gozney Group Limited annual accounts, Companies House company no. 07200046, FYs ended 31 March 2021–2024 (audited turnover; see `references/gozney_group_limited_accounts_*`); corroborated by [Gozney Grows Revenue by 62%, Expects to Close New Funding Round (CookOut News)](https://www.cookoutnews.com/gozney-grows-revenue-by-62-expects-to-close-new-funding-round/) and [Gozney Total Raised (CB Insights)](https://www.cbinsights.com/company/gozney/financials)
[^trends]: [Sourdough Searches Keep Surging 5 Years On (fooddrinklife.com)](https://fooddrinklife.com/sourdough-baking-trend-searches/); [homenewshere.com](https://homenewshere.com/national/features/article_7a6f4a67-fc72-5369-99f2-77a0d86b89c8.html)
[^flour-measure]: [How to Measure Flour (King Arthur Baking blog)](https://www.kingarthurbaking.com/blog/2023/10/13/measure-flour) — a "cup" of flour weighs ~120g using the fluff/spoon/level method but up to ~160g if scooped densely packed, a ~33% swing from technique alone.
[^oven-variance]: [Oven Accuracy and Calibration: Cook Better (ThermoWorks blog)](https://blog.thermoworks.com/thermal-secrets-oven-calibration/) — ovens set to the same nominal temperature have been measured varying by as much as 90°F unit-to-unit.
[^altitude]: [How to Bake Sourdough Bread at High Altitude (The Perfect Loaf)](https://www.theperfectloaf.com/how-to-bake-sourdough-bread-at-high-altitude/); [High Altitude Baking Adjustments (Elevation Baking)](https://www.elevationbaking.com/high-altitude-baking-adjustments)
[^forkish]: Forkish, K. (2012). *Flour Water Salt Yeast: The Fundamentals of Artisan Bread and Pizza.* Ten Speed Press. James Beard Award winner.
[^kenji]: López-Alt, J. K. (2015). *The Food Lab: Better Home Cooking Through Science.* W. W. Norton & Company. James Beard Award winner.