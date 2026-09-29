# BRAMBLE Model Report

A hierarchical Bayesian model predicting tree biomass (kg) from height (Ht) and crown
diameter (CD), fit separately per species but sharing statistical strength across species
(partial pooling). This report walks through what was built, how it was checked, and what
the results actually mean -- not just the numbers, but why each check exists.

## 1. Data
- Total trees: 240
- Species: Argan, Carob, Schinus, Olive, Eucalyptus
- Predictors: Ht, CD
- Train / test split: 192 / 48 trees (80/20, stratified by species
  so each species keeps its own proportion in both sets)

## 2. Model

    log(biomass) = beta0_species + b1_species*log(Ht) + b2_species*log(CD) + error

Biomass grows with size roughly as a power law, so fitting on the log scale turns that curve
into a straight line and keeps the error term's spread proportional to tree size rather than
constant in kg (which would badly overstate uncertainty for small trees and understate it for
large ones). Each species gets its own intercept and slopes, but those coefficients are drawn
from a shared population-level distribution -- species with fewer trees (Argan) borrow
statistical strength from the others instead of being fit in isolation. The model is fit with
MCMC (NUTS sampler in PyMC), using a non-centered parameterization, a numerical trick that only
helps the sampler converge and does not change what is being estimated.

## 3. Convergence (Step 7)
- Divergences: 2 (0 is ideal; a handful out of thousands of draws is not a concern)
- Max R-hat: 1.001 (target: as close to 1.00 as possible -- means the 4
  independent chains agree with each other)
- Min ESS: 1313 (effective sample size -- how many *independent*
  posterior draws the chains produced; higher is more precise)

These three numbers together say the sampler actually explored the posterior properly and the
fit can be trusted -- if any of them looked bad, nothing downstream would be reliable.

## 4. Overall + per-species performance (Step 9, training data)

**Overall (all species combined):** R2 = 0.851, RMSE = 164.07 kg,
CV% = 84.7%, Coverage = 85.4% (target ~80%).

An overall number can hide a species-specific weakness -- a few well-predicted species can
compensate for one badly-predicted one and the average would still look fine. The table below
splits the same predictions out by species:

| Species | R2 | RMSE | CV % | Coverage % | N trees |
| --- | --- | --- | --- | --- | --- |
| Argan | 0.27 | 15.90 | 106.70 | 64.70 | 34 |
| Carob | 0.84 | 20.72 | 38.60 | 94.70 | 38 |
| Schinus | 0.73 | 24.10 | 56.60 | 83.30 | 42 |
| Olive | 0.92 | 6.21 | 48.70 | 85.70 | 49 |
| Eucalyptus | 0.10 | 420.08 | 37.80 | 100.00 | 29 |

**Strongest fit:** Olive (R2 = 0.921). **Weakest fit:** Eucalyptus
(R2 = 0.100) -- Ht and CD alone carry little information for this species; see the
known limitation at the end of this report.

The figure below shows every tree's real biomass (x-axis) against the model's median
prediction (y-axis), with a bar for its P10-P90 uncertainty range, first for all species
pooled together and then one panel per species. A species with dots hugging the red 1:1 line
and narrow bars is one the model understands well from Ht+CD alone; a species with scattered
dots or wide bars relative to its size is one where those two predictors are not enough.

![Observed vs Predicted, overall and per species](report_figures/obs_vs_pred_per_species.png)

## 5. Calibration check (Step 8)

Coverage tells us *how often* the real value lands inside the predicted P10-P90 range,
but it can hide a lopsided pattern (e.g. systematically landing too high or too low even while
averaging to the right percentage). The histogram below shows, for every tree, where its real
value landed as a percentile of its own simulated distribution -- if the model is well
calibrated this should scatter evenly across 0-100. The scatter plot next to it is the same
observed-vs-predicted check as above, but on the full training set with the calibration
context.

![Calibration](report_figures/calibration.png)

## 6. Held-out test set (Step 10)

Training-set calibration can look good partly because the model was fit on those exact trees.
The real test is trees the model never saw during fitting:
- R2: 0.655
- RMSE: 191.77 kg
- Coverage: 81.2% (target ~80%)

With only 48 held-out trees, a single split's coverage number can swing quite a bit
just from which trees happened to land in the test set -- Section 8 checks this properly with
repeated cross-validation instead of relying on one split.

## 7. Per-tree prediction quality (Step 12)

Beyond one aggregate coverage number, this checks whether prediction quality depends on a
tree's size, age, or species -- i.e. whether the model is quietly worse for small trees, old
trees, or one particular species, which the aggregate numbers above would not reveal.
"Prediction density" here is how much probability mass the model puts exactly on the tree's
real value (computed on the log scale, so it is comparable across small and large trees alike).

![A few real trees, up close](report_figures/tree_density_examples.png)
![Prediction quality by size class, per species](report_figures/quality_by_size_species.png)

**Reading the boxplot:** dots outside a box are trees whose real value fell in a low-probability
region of their own predicted distribution -- i.e. trees the model predicted badly, not
necessarily trees outside their P10-P90 range (a related but stricter check). A species whose
line trends downward as trees get larger, while the others trend upward, is a species where the
model's confidence does not scale correctly with size -- watch for Eucalyptus here.

## 8. Normal vs Student-t likelihood comparison (Step 11)

The error term's shape (Normal vs Student-t, which has fatter tails and tolerates outlier trees
more easily) was compared three ways, because any single validation method can mislead on its
own:
- **80/20 split** -- coverage on the fixed held-out test set (Section 6).
- **5-fold cross-validation** -- 5 real refits, every tree held out exactly once, stratified by
  species; the most robust calibration check since it is not sensitive to one arbitrary split.
- **Leave-one-out (PSIS-LOO)** -- approximate leave-one-out on the full dataset, scored by ELPD
  (expected log predictive density): a stricter, different property than calibration -- how
  precisely probability mass is placed on the exact observed value, rather than whether the
  stated uncertainty range is honest.

| Likelihood | 80/20 Split -- Coverage % | 5-Fold CV -- Coverage % (mean +/- std) | Leave-One-Out -- elpd (+/- se) |
| --- | --- | --- | --- |
| Normal | 81.25 | 82.5 +/- 4.3 | -200 +/- 19 |
| Student-t | 70.83 | 69.6 +/- 3.2 | -170 +/- 17 |

![Normal vs Student-t](report_figures/normal_vs_studentt.png)

**Verdict:** kept **Normal** -- decided on 5-fold CV coverage, the validation method least
sensitive to any single arbitrary split, and the property the model's P10-P90 output is
actually used for. LOO/ELPD favored Student-t, and that is a real, non-trivial difference on
that specific metric -- but LOO triggered a Pareto-k warning on this data (its own diagnostic
flagging the approximation as less reliable here), and calibration and ELPD are two legitimately
different properties of the same fitted distribution that can disagree without either being
wrong. Calibration was chosen as the deciding factor because it is what the reported uncertainty
range is used for downstream.

## 9. Known limitation / next step

**Eucalyptus** remains the weakest species (R2 = 0.100 with Ht+CD alone); it also
needed the largest bias-correction factor when back-transforming from the log scale. This is not
a problem with the model itself (the hierarchy, priors, and sampler are all behaving correctly)
-- it is that height and crown diameter alone do not distinguish Eucalyptus trees well. Adding
basal diameter (BD) as a third predictor is the identified next step, specifically for this
species, and has not yet been applied in this version of the model.
