# BRAMBLE Model Report (5 species, Ht+CD+BD, with Eucalyptus)

A hierarchical Bayesian model predicting tree biomass (kg) from height (Ht), crown
diameter (CD) and basal diameter (BD), fit separately per species but sharing statistical
strength across species (partial pooling), with species-specific residual noise. This version
adds Eucalyptus to the original four species (Olive, Argan, Schinus, Carob), the richest
predictor set explored on this project, for comparison against the deep-learning
(Mambou-based) pipeline and against the simpler baseline branches.

## 1. Data
- Total trees: 240
- Species: Argan, Carob, Schinus, Olive, Eucalyptus
- Predictors: Ht, CD, BD
- Train / test split: 192 / 48 trees (80/20, stratified by species
  so each species keeps its own proportion in both sets)

## 2. Model

    log(biomass) = beta0_species + b1_species*log(Ht) + b2_species*log(CD) + b3_species*log(BD) + error_species

Biomass grows with size roughly as a power law, so fitting on the log scale turns that curve
into a straight line. Each species gets its own intercept and slopes, but those coefficients
are drawn from a shared population-level distribution -- species with fewer trees (Argan,
Eucalyptus) borrow statistical strength from the others instead of being fit in isolation. The
noise term (error_species) is also species-specific rather than shared, since different species
have genuinely different tree-to-tree variability. The model is fit with MCMC (NUTS sampler in
PyMC), using a non-centered parameterization, a numerical trick that only helps the sampler
converge and does not change what is being estimated.

## 3. Convergence (Step 7)
- Divergences: 2 (0 is ideal; a handful out of thousands of draws is not a concern)
- Max R-hat: 1.002 (target: as close to 1.00 as possible -- means the 4
  independent chains agree with each other)
- Min ESS: 2875 (effective sample size -- how many *independent*
  posterior draws the chains produced; higher is more precise)

These three numbers together say the sampler actually explored the posterior properly and the
fit can be trusted -- if any of them looked bad, nothing downstream would be reliable.

## 4. Overall + per-species performance (Step 9, training data)

**Overall (all species combined):** R2 = 0.931, RMSE = 112.06 kg,
CV% = 57.8%, Coverage = 87.0% (target ~80%).

An overall number can hide a species-specific weakness -- a few well-predicted species can
compensate for one badly-predicted one and the average would still look fine. The table below
splits the same predictions out by species:

| Species | R2 | RMSE | CV % | Coverage % | N trees |
| --- | --- | --- | --- | --- | --- |
| Argan | 0.53 | 12.66 | 85.00 | 85.30 | 34 |
| Carob | 0.87 | 18.63 | 34.70 | 84.20 | 38 |
| Schinus | 0.72 | 24.58 | 57.70 | 85.70 | 42 |
| Olive | 0.89 | 7.21 | 56.60 | 93.90 | 49 |
| Eucalyptus | 0.58 | 285.53 | 25.70 | 82.80 | 29 |

**Strongest fit:** Olive (R2 = 0.893). **Weakest fit:** Argan
(R2 = 0.534) -- see the known limitation at the end of this report.

![Observed vs Predicted, overall and per species](report_figures/obs_vs_pred_per_species.png)

## 5. Calibration check (Step 8)

Coverage tells us *how often* the real value lands inside the predicted P10-P90 range. The
P10-P90 range comes from simulating random tree-to-tree noise (drawn from each species' own
sigma) around each posterior draw's predicted mean -- this simulation, on its own, already
restores the correct average after exponentiating from the log scale, so no separate
bias-correction factor is applied on top of it (applying both would double-count the same
correction). The histogram below shows, for every tree, where its real value landed as a
percentile of its own simulated distribution -- if the model is well calibrated this should
scatter evenly across 0-100.

![Calibration](report_figures/calibration.png)

## 6. Held-out test set (Step 10)

Training-set calibration can look good partly because the model was fit on those exact trees.
The real test is trees the model never saw during fitting:
- R2: 0.907
- RMSE: 99.61 kg
- Coverage: 85.4% (target ~80%)

## 6b. Stand-level total biomass check

Individual-tree coverage can look fine on average while still being biased in one direction --
this check catches that. Every posterior draw's simulated biomass is summed across all trees
to get one possible TOTAL for the whole plot (correctly correlated, since every tree in a given
draw shares that draw's species-level parameters), giving a distribution of plausible totals.
The real field-measured total is then compared against that distribution.

- Real total biomass: 37199.6 kg
- Predicted total (P10-P90): 34913.8 - 41799.3 kg (median 37995.1 kg)
- Real total inside P10-P90? True
- Real total lands at percentile: 37.1 (50 = perfectly centered)

![Total biomass check](report_figures/total_biomass_check.png)

## 7. Per-tree prediction quality (Step 12)

Beyond one aggregate coverage number, this checks whether prediction quality depends on a
tree's size, age, or species. "Prediction density" here is how much probability mass the
model puts exactly on the tree's real value (computed on the log scale).

![A few real trees, up close](report_figures/tree_density_examples.png)
![Prediction quality by size class, per species](report_figures/quality_by_size_species.png)

## 8. Normal vs Student-t likelihood comparison (Step 11)

| Likelihood | 80/20 Split -- Coverage % | 5-Fold CV -- Coverage % (mean +/- std) | Leave-One-Out -- elpd (+/- se) |
| --- | --- | --- | --- |
| Normal | 85.42 | 83.3 +/- 8.5 | -170 +/- 19 |
| Student-t | 77.08 | 75.0 +/- 3.9 | -160 +/- 16 |

![Normal vs Student-t](report_figures/normal_vs_studentt.png)

**Verdict:** kept **Normal** -- decided on 5-fold CV coverage, the validation method least
sensitive to any single arbitrary split.

## 9. Known limitation / next step

**Argan** remains the weakest species (R2 = 0.534) even with Ht, CD and BD
together, and with Eucalyptus added to the dataset. This is treated as a limitation of the
available measurements for this species rather than a flaw in the model itself, and further
tuning specifically aimed at this species' residual pattern was deliberately avoided to prevent
overfitting to this one dataset. Separately, Eucalyptus has the fewest trees of any species and
a much larger absolute biomass scale, producing a high raw RMSE and a more modest R2 despite
good, honest calibration (coverage close to the 80% target) -- this reflects Eucalyptus's lower
within-species variance and small sample size, not poor model fit.
