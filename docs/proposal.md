---
title: "CUNY MSDS Capstone Project Proposal"
author: "Kevin Havis"
date: today
abstract: >
  This project will explore the ability to encode, classify, and optimize
  culinary recipes towards a target culinary style, a relatively unexplored
  space in supervised learning, by piloting an approach based on pizza dough
  classifications. The project will generate a curated, labeled, and
  normalized dataset of expert recipes to establish style centroids, then
  compare supervised machine learning approaches. Finally, I will develop a
  constrained optimization approach to guide new formulations towards
  preferred culinary styles, encapsulating the project in a usable recipe
  formulation tool.
format:
  pdf:
    documentclass: article
    papersize: letter
    fontsize: 11pt
    geometry:
      - margin=1in
    linestretch: 1.15
    number-sections: true
    number-depth: 2
    toc: true
    toc-depth: 2
    colorlinks: true
    fig-pos: "H"
---

## Problem Statement

The culinary arts are a complex subject area and an interesting area of potential optimization. It is a difficult domain to model with data due to its many hard-to-measure features, such as the wide range of ingredients, the specificity of heat and time measurements, the various techniques and steps, and the evaluation of the results. Culinary dishes often do not present well as an optimization problem, as maximizing taste or texture, for example, is not objective. As such, there is little applied data science in the domain.

One sub-domain that circumvents some of these issues is baking. Many baking recipes involve a small list of ingredients, as few as four in many cases - salt, water, flour, and yeast. Additionally, it is quite common to represent these (and any other ingredients) as "baker's percentages", as a percentage of the amount of flour used. These formulations solve the aforementioned specificity and measurement problems. Unfortunately, if we are interested in optimizing these formulations towards a specific outcome, we must be able to describe and label such outcomes (as classes) consistently. For baking broadly, this is not feasible due to the very large number of potential classes. For this reason, we are specifically interested in pizza dough formulations.


Pizza is one of the most popular foods in the world, is an accessible product for many home cooks, and has a readily available corpus of recipes. It is also commonly represented in, or can be converted to, baker's percentages. Pizza has distinct, well-recognized regional styles, which allow us to optimize a formulation towards a specific style (such as "New York" or "Neapolitan"), and as such it is an ideal candidate for a pilot study of culinary optimization.

Additionally, the consumer pizza equipment sector has grown considerably. Manufacturers specializing in dedicated pizza equipment, such as Ooni and Gozney, have seen remarkable market growth. Gozney Group Limited's filed UK accounts show turnover rising from £12.9M in the financial year ended 31 March 2021 to £60.7M in the year ended 31 March 2024 - four consecutive years of compounding growth, at +111%, +62%, and +37% respectively.[^gozney] Its closest competitor, Ooni, is reported to have reached roughly $200M in annual revenue at its peak, easing to approximately $194M in 2023 as pandemic-era demand normalized.[^ooni]

In addition, the interest in recipes for specific styles has also increase. Among the rising US pizza dough queries of the five years to September 2026, four of the fifteen highest-volume are Neapolitan-specific: "neapolitan pizza dough recipe" and "neapolitan pizza" both carry a search-interest index of 24, and "neapolitan pizza dough" and "neapolitan pizza recipe" both carry 23.[^trends]. This indicates real consumer interest in the formulation of specific pizza dough styles.

![](figures/pizza_dough_rising_queries_light.pdf){fig-align="center" width="90%"}

*Figure 1. The fifteen highest-volume rising US pizza dough search queries, September 2021 - September 2026*


The core question the project will answer is, *can a low dimensional, domain-informed representation of dough formulations distinguish well-defined pizza styles sufficiently to enable recipe adjustment recommendations and optimizations?*

To this end, the project will cover data representations, classification, similarity scoring, and constrained optimization algorithms.


## Data

Labeled pizza formulations are not readily available as structured data. As such, the project will contribute a small, well-structured dataset of expert-curated recipes. By focusing on expert recipes, we can establish clear profiles of each pizza style against which to measure other formulations. Imposing constraints will allow us to be confident in our class labels, but will require us to limit our training data - this, however, is not expected to detract from the project given our approach.

We are deliberately deciding to ignore dough processing steps and other parameters, as including them would dramatically increase the scope of this project.

### Sourcing

The dataset will be built by ethically sourcing a corpus of recipes from well-known sources such as King Arthur Baking, Ooni, James Beard Award-winning authors, and pizza-focused online forums. Scraping will be done manually, will abide by site policies, and will be credited in the final data.

|Style|*n* Processed Recipes|
|--|--|
|Neapolitan|11 |
|New York| 12|
|Sicilian|9| 
|**Total**| **32**|

The recipes will be manually entered into a pre-defined data schema. Conversions and conventions for normalizing the ingredients will be defined, established, and followed to ensure consistency and standardization of the recipes. Only the "dough" section of the recipe will be extracted. Each recipe is stored with its style label, source, original raw text, and the resulting normalized ingredient percentages (flour, water, salt, yeast, fat, and sugar, each as a baker's percentage of flour), alongside the extraction method used for each field, so every conversion is traceable back to its source text.

### Processing

The recipes will be labeled based on the recipe title, description, or other clearly labeled context, such as forum topics. We will limit the styles to "New York", "Neapolitan", and "Sicilian".

The steps to extract, convert, and normalize will be encoded along with the original raw text and output data for reproducibility and transparency. All conversions and mappings, such as reconciling naming variants like "instant", "rapid-rise", and "IDY" to a single yeast type, are explicitly defined in code.

```{{json}}
  {
    "recipe_id": "neapolitan_001",
    "style": "neapolitan",
    "source": "https://www.seriouseats.com/basic-neapolitan-pizza-dough-recipe",
    "flour": 100.0,
    "flour_type": "bread",
    "water": 65.0,
    "salt": 2.0,
    "yeast": 1.5,
    "yeast_type": "instant",
    "fat": 0.0,
    "fat_type": null,
    "sugar": 0.0,
    "sugar_type": null
  }
```

## Style Centroid Calculation

The expert-defined recipes will be used to calculate *style centroids* in the feature space, based on their labels. This will provide us a neighborhood of canonical formulations for each style.

I will then define affinity scores for each recipe across each style. This will serve two purposes:

1. Check against the expert classification of the styles
2. Provide a baseline against which to measure other supervised learning methods

## Supervised Learning - Style Classification

Once the affinity score baselines are established, I will explore various supervised classification techniques and models to see if the formulations are sufficient to distinguish between the three styles. Due to the small size of the dataset, I will use stratified k-fold cross-validation for evaluation. Models will be evaluated with typical classification metrics, including F1, accuracy, and confusion matrix analysis.

The goal of this step is to explore if the models can approximate expert labels from the formulations themselves.

## Optimization

Optimization in this context refers to allowing a formulation to be improved towards a specific outcome. This is where the subjectivity of culinary preferences can be explored - an individual's ideal pizza formulation may not be a true "New York Style", but perhaps a blend of New York Style and Neapolitan. Thus the *constrained optimization problem* is to take a recipe and minimally adjust it to maximize the "blend" specified. In plain language, can we take a New York Style recipe and move it closer to a Neapolitan style by $X\%$?

## User Interface

As a way to interact with the models and optimization algorithm, I will develop a user interface where users can input their own formulations and retrieve an affinity-score classification, adjust towards a target style, and set other variables.

## Project Outcome

The project will deliver a conclusion to the research question, a curated dataset of labeled, expert pizza dough formulations, and a deployed user interface for recipe development.

## Future Scaling

There is great potential for this approach to be expanded. Below are a few ways the project could be scaled.

- Include and encode full dough processing steps, including mixing, bulk fermentation, shaping, etc.
- Add additional recipes using the established schema & conventions
- Expand the class targets to include other unenriched doughs, including classic representations like baguettes, boules, and loaves
- Develop nutritional profiles using the specific and measurable ingredients
- Extend the framework to other, more complex culinary applications, such as desserts or pastries

[^gozney]: Gozney Group Limited, annual accounts, Companies House company no. 07200046

[^ooni]: Ooni Limited  Annual Report and Consolidated Financial Statements no. 08316049

[^trends]: Google Trends, US web search, "rising queries" report for pizza dough, September 2021 - September 2026 (retrieved 22 September 2026). The reported percentages are Google's rounded growth figures for each query over the period.
