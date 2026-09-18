# CUNY MSDS Capstone Project Proposal

Author: Kevin Havis

## Abstract

This project will explore the ability to encode, classify, and optimize culinary recipes to achieve specific, well-defined culinary styles, a relatively unexplored space.

The project will pilot this approach with pizza recipes, due to the availability, popularity, well established culinary styles, and consistency of ingredients and process. 

I will generate a curated, labeled, and normalized dataset of expert recipes to establish style centroids, then compare supervised machine learning approaches. Finally, I will develop a constrained optimization approach to guide new formulations towards preferred culinary styles, encapsulating the project in a usable recipe formulation tool.

## Problem Statement

The culinary arts are a complex subject area and an interesting area of potential optimization. It is a difficult domain to model with data due to the many, hard-to-measure features, and it often does not present well as an optimization problem. Maximizing taste or texture is not a clear or straightforward task. As such, there is little applied data science to the domain.

One sub-domain that lends itself well to normalized data representation is baking. Many baking recipes involve very few ingredients, as little as four in many cases - salt, water, flour, and yeast. Additionally, it is quite common to represent these (and any other ingredients) as "baker's percentages", as a percentage of the amount of flour used. Unfortunately, even these simple combinations results in many hundreds of possible outcomes based on other factors that are less readily available.

To address this, I propose to use pizza dough formulations. Pizza is one of the most popular foods in the world, is accessible for many home cooks, and a readily available corpus of recipes. It also makes use of a small list of ingredients expressed in baker's percentages, and as such is an ideal candidate for a pilot study of culinary optimization. Optimization, in this case, will refer to the aligning of a formulation to well-known and desirable styles, such as "New York Style", "Neopolitan", or "Sicillian".

The core question the project will answer is, *can a low dimensional, domain-informed representation of dough formulations distinguish well-defined pizza styles sufficiently to enable recipe adjust recommendations and optimizations?*

To this end, the project will cover data representations, classification, similarity scoring, and constrained optimization algorithms.

## Data

Labeled pizza formulations are not readily available as structured data. The project will contribute a small dataset of expert-curated recipes. By focusing on expert recipes, we can establish clear profiles of each pizza style against which to measure other formulations.

We are deliberately deciding to ignore dough processing steps and other parameters as part of this initial scope.

### Sourcing

The dataset will be built by ethically sourcing a corpus of recipes from well known sources such as King Arthur Baking, Ooni, James-Beard award winning authors, and pizza-focused online forums. Scraping will be done manually, abide by site policies, and be credited in the final data.

|Style|*n* Processed Recipes|
|--|--|
|Neopolitan|11 |
|New York| 12|
|Siciliian|9| 
|**Total**| **32**|

The recipes will be manually entered into a pre-defined data schema. Conversions and conventions for normalizing the ingredients will be defined, established, and followed to ensure consistency and standardization of the recipes. Only the "dough" section of the recipe will be extracted.

```python
# Example of normalized
class YeastType(Enum):
active_dry = "active-dry"
instant = "instant"
fresh = "fresh"
sourdough_starter = "sourdough-starter"  # includes poolish

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
```


### Processing

The recipes will be labeled based on the recipe title, description, or other clearly labeled context, such as forum topics. We will limit the styles to "New York", "Neopolitan", and "Siciliian".

The steps to extract, convert, and normalize will be encoded along with the original raw text and output data for reproduceability and transparency. All conversions and mappings are explicitly defined in code.

Below is an example of a recipe in the prescribed format.

```json
{
"recipe_id": "neapolitan_001",
"style": "neapolitan",
"source": "https://www.seriouseats.com/basic-neapolitan-pizza-dough-recipe",
"raw_text": "20 ounces (about 4 cups) bread flour, preferably Italian-style \"OO\"\n.4 ounces kosher salt (about 4 teaspoons)\n.3 ounces (about 2 teaspoons) instant yeast, such as SAF Instant Yeast\n13 ounces water",
"mapping": {
    "flour": {
    "raw": "20 ounces ... bread flour",
    "method": "to_grams(oz->g); baker's-percentage anchor"
    },
    "flour_type": {
    "raw": "bread flour, preferably Italian-style \"OO\"",
    "method": "match_alias",
    "note": "named 'bread flour' but author prefers Italian-style 00; matched literal name, not preference (text says letter-O 'OO', not digit '00', so alias didn't fire on 00 anyway)"
    },
    "water": {
    "raw": "13 ounces water",
    "method": "to_grams + to_baker_percentage"
    },
    "salt": {
    "raw": ".4 ounces kosher salt (about 4 teaspoons)",
    "method": "to_grams + to_baker_percentage"
    },
    "yeast": {
    "raw": ".3 ounces (about 2 teaspoons) instant yeast",
    "method": "to_grams + to_baker_percentage"
    },
    "yeast_type": {
    "raw": "instant yeast",
    "method": "match_alias"
    },
    "fat": {
    "raw": "(not present in source)",
    "method": "manual",
    "note": "no fat ingredient in source; defaulted to 0"
    },
    "fat_type": {
    "raw": "(not present in source)",
    "method": "manual",
    "note": "no fat ingredient in source; defaulted to 0"
    },
    "sugar": {
    "raw": "(not present in source)",
    "method": "manual",
    "note": "no sugar ingredient in source; defaulted to 0"
    },
    "sugar_type": {
    "raw": "(not present in source)",
    "method": "manual",
    "note": "no sugar ingredient in source; defaulted to 0"
    }
},
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

I will then define affinity scores for each recipe across each style. This will serve two purposes;

1. Check against the expert classification of the styles
2. Provide a baseline against which to measure other supervised learning methods

## Supervised Learning - Style Classification

Once the affinity score baselines are established, I will explore various supervised classification techniques and models to see if the formulations are sufficient to distinguish between the three styles. Due to the small size of the dataset, I will use stratified cross fold validation on the results. Models will be evaluated with typical classification metrics, including F1, accuracy, and confusion matrix analysis.

The goal of this step is to explore if the models can approximate expert labels from the formulations themselves.

## Optimization

Optimization in this context refers to allowing a formulation to be improved towards a specific outcome. This is where the subjectivity of culinary preferences can be explored - an individual's ideal pizza formulation may not be a true "New York Style", but perhaps a blend of New York Style and Neopolitan. Thus the *constrained optimization problem* is to take a recipe and minimally adjust it to maximize the "blend" specified. In plain language, can we take a New York Style recipe and move it closer to a Neopolitan style by $X%$?

If the scope allows, this section will also attempt to handle environmental variables and constraints, such as flour type limitations, atmospheric pressure, and equipment, which all contribute significantly to overall results.

## User Interface

As a way to interact with the models and optimization algorithm, I will develop a user interface where users can input their own formulations and retrieve a affinity-score classification, adjust towards a target style, as well as other variables.

## Project Outcome

The project will deliver a conclusion the the research question, a curated dataset of labeled, expert pizza dough formulations, a deployed user interface for recipe developement.

## Future Scaling

There is great potential for this approach to be expanded. Below are a few ways the project could be scaled

- Include and encode full dough processing steps, including mixing, bulk fermentation, shaping, etc.
- Add additional recipes using the established schema & conventions
- Expand the class targets to include other unenriched doughs, including classic representations like baguettes, boules, and loaves
- Develop nutritional profiles using the specific and measurable ingredients
- Leverage the framework to other more complex culinary applications, such as desserts or pastries