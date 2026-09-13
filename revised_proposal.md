Absolutely. With a **small, expert-reviewed and classified corpus**, the project becomes much stronger if you position it as a **data-driven representation, classification, and optimization system**, rather than primarily a recipe-generation tool.

 ## Proposed Capstone Direction

 ### Working concept

 **A data-driven framework for representing, classifying, and optimizing pizza dough formulations under culinary and physical constraints.**

 The system takes a pizza dough formulation and its preparation process, represents both as structured data, predicts its **stylistic affinity**, and recommends changes that move the formulation toward a desired style while respecting real-world constraints.

 The pizza application is the domain; the capstone is fundamentally about **feature representation, classification, similarity, and constrained optimization**.

---

 ## 1\. Build a curated expert corpus

 The foundation is a relatively small but high-quality dataset of recipes that have been **reviewed and classified by knowledgeable experts**.

 Each recipe should ideally contain:

 - Ingredient quantities
- Baker's percentages
- Flour characteristics
- Hydration
- Salt, yeast, oil, sugar, etc.
- Preferment information
- Fermentation duration and temperature
- Mixing/kneading methodology
- Balling/proofing methodology
- Baking temperature and duration
- Baking surface/oven type
- Other meaningful procedural information
- Expert-assigned pizza style(s)

 The corpus doesn't need to be huge. Its value comes from **quality, provenance, consistency, and expert labeling**.

 Importantly, preserve the original recipe as well as your normalized representation so that your preprocessing is reproducible.

---

 ## 2\. Develop a structured recipe representation

 This is one of the core data-science problems.

 Transform heterogeneous recipes into a standardized representation.

 For example:

 **Formulation vector**

 $$
X_f =
[
hydration,\ flour\ type,\ salt\%, yeast\%, oil\%, sugar\%, preferment\%, ...
]
$$

 **Process vector**

 $$
X_p =
[
fermentation\ time,\ fermentation\ temp,\ mixing,\ proofing,\ bake\ temp,\ bake\ time,\ oven\ type,\ ...
]
$$

 You can also investigate textual representations of instructions rather than reducing everything to manually defined categorical variables.

 The important research question becomes:

 > **What representation of a pizza recipe best captures stylistic similarity?**

---

 ## 3\. Establish a deterministic baseline

 Start with a deliberately simple model.

 For example:

 - Baker's percentage rules
- Expert-defined weights
- Style centroids
- Euclidean/cosine distance

 A recipe can then be compared to each style centroid.

 For example:

```
Neapolitan       0.72
New York         0.18
Sicilian         0.07
Roman            0.03
```

 These should be interpreted as **style affinity**, not necessarily literal probabilities.

 This baseline is important because it gives you something against which to evaluate more data-driven approaches.

---

 ## 4\. Compare alternative predictive models

 This is where the project becomes a genuine data-science study.

 Using the expert-labeled corpus, investigate whether learned models outperform the deterministic similarity model.

 Potential approaches include:

 - k-nearest neighbors
- Logistic regression
- SVM
- Random forest / gradient boosting
- Clustering
- Dimensionality reduction
- Text/semantic embeddings
- Hybrid ingredient + process representations

 You don't need to use all of these.

 A particularly clean capstone would compare:

 > **Expert rules → centroid model → supervised classifier → learned/semantic representation**

 and determine which representation produces the most meaningful classifications.

---

 ## 5\. Evaluate against expert judgment

 This is probably the most important addition to the original concept.

 The question shouldn't simply be:

 > “Can my model reproduce the labels I gave it?”

 Instead:

 > **“Does the model's notion of stylistic similarity agree with knowledgeable human judgment?”**

 You can evaluate:

 - Classification accuracy
- Precision/recall/F1
- Confusion matrix
- Similarity ranking
- Agreement with expert classifications
- Inter-rater agreement, if multiple experts are available

 For ambiguous recipes, you could explicitly allow multiple styles or affinity scores.

 That makes the system much more realistic than forcing every recipe into one categorical bucket.

---

 # 6\. Add constrained recipe optimization

 This is where the project moves beyond classification.

 Given:

 > **Current formulation + desired style**

 the system determines what changes would most efficiently move the formulation toward the target.

 For example:

```
Current formulation
       ↓
Style representation
       ↓
Distance from target
       ↓
Candidate modifications
       ↓
Constraint checking
       ↓
Optimized formulation
       ↓
Predicted style affinity
```

 The optimization objective could be something like:

 > **Minimize formulation/process changes while maximizing affinity to the target style.**

 That is a substantially more interesting problem than simply saying "increase hydration."

---

 ## 7\. Treat real-world constraints explicitly

 The recommendation engine should account for constraints such as:

 ### User constraints

 - Available flour
- Available ingredients
- Desired fermentation time
- Desired pizza size
- Skill level
- Equipment

 ### Physical constraints

 - Oven maximum temperature
- Oven type
- Baking surface
- Ambient temperature
- Altitude

 Some of these can initially be **deterministic domain-knowledge adjustments** rather than ML.

 That's completely fine.

 In fact, I'd explicitly separate them:

 > **Predictive model:** What formulation/process characteristics correspond to a style?

 > **Constraint engine:** What recommendations are physically and practically feasible for this user?

 That separation makes the architecture much easier to defend academically.

---

 # 8\. Validate the recommendation system

 Classification is relatively straightforward to evaluate.

 Recommendations are harder.

 You could evaluate whether:

 1. The system's proposed changes move the recipe closer to the target style in feature space.
2. The resulting recipe receives a higher predicted style affinity.
3. Experts agree that the modified recipe is closer to the target style.
4. The system produces sensible recommendations under ingredient/equipment constraints.

 Ideally, you would have experts evaluate **before/after formulations**.

 For example:

 > Original → Modified

 and ask:

 > "Is the modified formulation more Neapolitan?"

 That gives you an empirical test of the optimization component.

---

 # The resulting architecture

 The complete capstone could therefore look like:

```
                  EXPERT-CURATED CORPUS
                           │
                           ▼
                 Recipe normalization
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      Formulation representation    Process representation
             │                           │
             └─────────────┬─────────────┘
                           ▼
                  STYLE REPRESENTATION
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
       Baseline model              Predictive models
       (rules/centroids)           (ML/embeddings)
             │                           │
             └─────────────┬─────────────┘
                           ▼
                  STYLE AFFINITY
                           │
                           ▼
                 TARGET STYLE SELECTED
                           │
                           ▼
               CONSTRAINED OPTIMIZATION
                           ▲
                           │
             ┌─────────────┼─────────────┐
             │             │             │
        ingredients     equipment      environment
             │             │             │
             └─────────────┴─────────────┘
                           │
                           ▼
                 RECOMMENDED FORMULATION
                           │
                           ▼
                   EXPERT VALIDATION
```

 ## What makes this a graduate-level data-science project?

 The strongest research questions become:

 1. **Representation:** How should recipes and processes be encoded to capture culinary style?
2. **Classification:** Can a model distinguish pizza styles from formulation and process characteristics?
3. **Similarity:** Does computational similarity correspond to expert perceptions of stylistic similarity?
4. **Optimization:** Can the system identify formulation/process changes that move a recipe toward a target style?
5. **Constraints:** Can those changes be optimized while respecting real-world ingredient, equipment, and environmental limitations?

The **recipe tool is the deliverable**. The actual academic contribution is the investigation of these questions.

And because you'll have access to an **expert-reviewed corpus**, you have a particularly good opportunity to make the project rigorous despite the relatively small dataset. I'd lean into that rather than trying to compensate for the small sample with unnecessarily sophisticated ML. A well-designed experiment on 100–300 excellent recipes is considerably more defensible than a model trained on thousands of noisy web recipes.

--AFTER SMALL DATASET FEEDBACK---
Yes, but **bootstrapping won't really solve the underlying low-sample problem** if you mean taking your \~30 recipes and resampling them to create, say, 300 or 3,000 recipes.

 ### The key distinction

 Suppose you have:

 - 10 New York recipes
- 10 Neapolitan
- 10 Detroit

 You can bootstrap those 10 recipes many times, but every bootstrap sample is still ultimately based on those **same 10 observations**.

 So you might get:

 > 10 originals → 1,000 bootstrap samples

 but you **do not get the statistical information of 1,000 independent recipes**.

 In fact, with only 10 observations per class, bootstrap estimates of things like variance/tolerance can themselves be quite unstable.

 ### Where bootstrapping _would_ help

 It could be quite useful for **uncertainty estimation and robustness testing**.

 For example, for each class:

 1. Resample the 10 recipes with replacement.
2. Calculate your centroid/tolerance.
3. Score a held-out recipe.
4. Repeat 1,000 times.
5. Examine how much the centroid and classification probability move.

 You might discover something like:

 > New York: 72% ± 8%\
>  Neapolitan: 21% ± 7%\
>  Detroit: 7% ± 3%

 That is much more informative than simply reporting:

 > New York: 72%

 You could also use bootstrap samples to answer:

 **“Does my model's conclusion depend heavily on one particular recipe?”**

 That's a genuinely valuable use of bootstrapping here.

---

 ## I'd actually change your approach slightly

 Your proposal currently says:

 > “centroids will be anchored in published expert formulas ... with the curated recipes used to estimate the acceptable variation”

 That's actually a **good response to the small-N problem**.

 I'd lean into it rather than trying to manufacture additional observations.

 Think of your data as having two components:

 **1\. Prior/domain knowledge**

 Expert formulas establish what you believe the center of each style should be.

 **2\. Empirical observations**

 Your \~10 recipes/class establish how much real-world recipes vary around that center.

 You could formulate this statistically as something like a **Bayesian/shrinkage model**, although you don't necessarily need to implement a sophisticated Bayesian model for the project.

 Conceptually:

 $$
\text{Estimated centroid}
=
\text{expert prior}
+
\text{evidence from curated recipes}
$$

 This is much more defensible than pretending that 10 recipes give you a precisely estimated population centroid.

 ### And there's another trick that's probably more valuable than synthetic bootstrapping

 **Feature-level augmentation.**

 Your recipes are formulas. That gives you an unusual opportunity.

 Suppose you have:

 > Flour: 100%\
>  Water: 65%\
>  Salt: 2.5%\
>  Yeast: 0.2%

 You could generate legitimate **recipe variants** by applying transformations that preserve the style:

 - Scale the entire recipe.
- Convert between equivalent units.
- Adjust total dough weight.
- Represent fermentation schedules in standardized units.
- Potentially perturb parameters within empirically justified ranges.

 But be careful: these aren't independent observations either. I'd call them **augmented observations**, not additional recipes.

 They can be useful for testing the _mechanics_ of your system, but you shouldn't use them to claim:

 > “We now have 3,000 recipes.”

 You still have 30 underlying recipes.

---

 ## Your biggest issue may actually be dimensionality

 This is where I'd be more concerned than the 30/3 number.

 Imagine each recipe gets 15–30 features:

 - hydration
- salt %
- yeast %
- oil %
- sugar %
- flour protein
- preferment %
- fermentation time
- fermentation temperature
- bulk time
- proof time
- baking temperature
- bake time
- dough thickness
- etc.

 With \~10 examples/class, estimating a covariance structure in 20 dimensions is essentially hopeless.

 And if you calculate ordinary Euclidean distance, you're implicitly saying:

 > 1 unit of fermentation-time difference is commensurate with 1 unit of hydration difference, etc.

 That's a much more consequential modeling assumption than whether you have 30 vs. 300 samples.

 I'd therefore strongly consider:

 - **a relatively small number of carefully chosen features**
- domain-informed feature weights
- standardized features
- simple distance metrics
- expert-defined centroids
- bootstrap uncertainty around the resulting scores

 rather than a high-dimensional machine-learning classifier.

---

 ## Three classes isn't actually a problem

 In fact, **three classes is probably an advantage for this project**.

 You aren't trying to build:

 > “The world's universal pizza classifier.”

 You're demonstrating:

 > “Can a parameterized recipe representation distinguish several well-defined dough styles and provide useful directional adjustments?”

 That's a very reasonable research question.

 You could even make the experiment deliberately:

 ### Research question

 > **Can a low-dimensional baker's-percentage and technique representation distinguish three well-defined pizza dough styles sufficiently well to provide useful recipe-adjustment recommendations?**

 Then your 30 recipes become a **pilot dataset** rather than an embarrassment.

---

 ## What I'd do with \~30 recipes

 I'd probably structure the experiment something like:

 |  | NY | Neapolitan | Detroit |
| --- | --- | --- | --- |
| Recipes | 10 | 10 | 10 |
| Training | 7 | 7 | 7 |
| Test | 3 | 3 | 3 |

Then repeat the train/test split many times using **stratified repeated cross-validation**.

 For every training set:

 1. Establish the centroid from your expert/domain information.
2. Estimate tolerance from the training recipes.
3. Classify the held-out recipes.
4. Record accuracy / confusion matrix.
5. Repeat across many splits.

 And separately use bootstrapping to estimate uncertainty around your metrics.

 With only 30 observations, I would **not** make a big deal out of a metric like:

 > Accuracy = 86.7%

 Instead report something like:

 > “The classifier achieved X% accuracy under repeated stratified cross-validation, with substantial uncertainty due to the small curated dataset.”

 And show the confusion matrix.

---

 ### One important warning

 Don't bootstrap your way into **data leakage**.

 If you make 100 augmented/bootstrap versions of a recipe, then put some versions into training and others into your test set, your test performance can look spectacular while telling you almost nothing about generalization.

 The fundamental unit for your train/test split should remain the **original recipe**.

 So:

 > Recipe A → all its bootstrap/augmented variants

 must stay entirely in either training **or** testing.

---

 ### Bottom line

 **Yes, bootstrap—but use it to quantify uncertainty, not to pretend you have a larger dataset.**

 For your particular proposal, I'd be quite comfortable with **\~30 carefully curated recipes across 3 classes** if you present it as a **small-data, domain-informed classification/prototype study**. The expert-anchored centroids are actually a compelling way to address the small-N issue.

 If this is for a thesis/capstone/research project, I would actually argue that **the interesting research contribution is the representation + domain-informed distance model \+ uncertainty**, rather than trying to compete with a conventional ML classifier on sample size.