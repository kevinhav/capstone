# Pizza dough style classification & adjustment

CUNY MSDS capstone: can a low-dimensional, domain-informed representation of dough
formulations distinguish pizza styles well enough to recommend recipe adjustments?
See [docs/proposal.md](docs/proposal.md) and [docs/project_plan.md](docs/project_plan.md).

## Setup

```bash
uv sync
uv run pytest
```

## Layout

```
src/capstone/
  config.py      paths, StrEnums (styles, ingredient types, columns), tunable configs
  data.py        Recipe contract, unit/ingredient conversions, load_recipes, make_frankensteins
  features.py    preprocessing (z-scored ratios + one-hot types), feature names, bounds, Gower distance
  models/
    centroids.py style centroids, affinity, blended targets, estimate_mix, AffinityClassifier
    adjust.py    minimal-change adjustment toward a style or style mix
    network.py   recipe/centroid graph
    artifacts.py build_artifacts(): fitted model + processed outputs
  utilities.py   logging, model pickling, JSON/JSONL caches
  app/           Streamlit app (app.py) and its plots
data/raw/        curated recipes (immutable) + schema and intake notes
data/interim/    temporary cached results (not committed)
data/processed/  derived outputs: recipes.jsonl, features.jsonl, centroids.json
models/          pickled fitted pipelines (not committed)
notebooks/
  explore/       working analysis: 01 EDA, 02 centroids/network, 03 classification,
                 04 constrained optimization, 05 blended targets (not committed)
  present/       notebooks for final presentation
```

## Usage

```python
from capstone.data import Recipe, load_recipes
from capstone.models import adjust, build_search_space, estimate_mix, load_or_fit_centroids

recipes = load_recipes()
pipe = load_or_fit_centroids(recipes)          # cached under models/, refit if data or sklearn changes
space = build_search_space(pipe, recipes)

mine = Recipe(flour_type="high-gluten", water=62, salt=2.5, yeast=0.4, yeast_type="instant").to_row()
result = adjust(mine, {"new-york": 70, "neapolitan": 30}, space)
result.recipe, result.loss, result.n_type_changes
```

Rebuild cached outputs: `uv run python -c "from capstone.models import build_artifacts; build_artifacts()"`

Run the app: `uv run streamlit run src/capstone/app/app.py`
