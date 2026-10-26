# XGBoost and Rental Prediction: Critical Review

## Algorithm and complexity

Friedman's functional-gradient formulation explains additive learning and the
interaction between shrinkage, iterations, tree structure, and loss. XGBoost
adds a regularized tree objective and practical split/system optimizations.
Its core objective can be written as prediction loss plus a leaf-count penalty
and squared-leaf-weight penalty. These are reasons to inspect complexity and
regularization, not proof that the selected rent model generalizes.
[P15](https://doi.org/10.1214/aos/1013203451),
[P14](https://arxiv.org/pdf/1603.02754).

DhakaNest should report the saved objective, target transform, depth, learning
rate, estimator count, sampling, regularization, preprocessing, search budget,
and selection split from its own evidence. Squared-error loss can emphasize
large residuals; evaluating in BDT after a log target requires explicit inverse
transformation and residual diagnostics. This is a project analysis requirement,
not a new claim about a published result.

## Structured data and alternatives

The 45-dataset tabular benchmark supports tree ensembles under its tested
medium-sized regimes and examines irrelevant features and target irregularity.
Random forests provide an averaging-based alternative; CatBoost addresses
categorical target leakage and ordered learning. These sources justify the
project's RF/CatBoost/XGBoost comparison without implying a universal winner.
[P19](https://proceedings.neurips.cc/paper_files/paper/2022/file/0378c7692da36807bdec87ab043cdadc-Paper-Datasets_and_Benchmarks.pdf),
[P16](https://doi.org/10.1023/A:1010933404324),
[P17](https://arxiv.org/pdf/1706.09516).

Location encoding, rare-area support, and leakage-free preprocessing deserve
particular scrutiny in Dhaka. Lowest observed validation MAE selects a model
within this experiment; it does not establish superiority across all markets,
splits, or tuning budgets.

## Local rental evidence

The Dhaka explainable-prediction paper P20 reports voting-ensemble MAE 2,536.77,
RMSE 4,398.23, R2 0.86, and MAPE 11%. These figures describe that study only.
Its scaling rationale and evaluation design warrant scrutiny. DhakaNest's
official MAE 3,193.69 BDT, RMSE 7,667.50 BDT, R2 0.9001, and MAPE 11.88% use
different preparation and splits. The metrics cannot establish which model is
better across papers. [P20](https://ieomsociety.org/proceedings/2023dhaka/146.pdf).

Section 4 of P20 reports 28,800 Bproperty observations collected during
February-April 2022. DhakaNest's raw manifest also records 28,800 rows. This is
evidence of potentially overlapping provenance, not verified byte-level identity.
Confirm source lineage and cleaning differences before presenting the project as
an independently collected market dataset.

The earlier 2014 Dhaka ANN paper (S32) is explicitly deferred because venue and
data-description verification are incomplete. Its existence should not be
turned into an accepted performance comparison.

## Explanation and uncertainty

SHAP gives model-relative local attributions with explicit axioms; the choice
of background distribution and transformed features affects interpretation.
Attributions do not establish causal neighborhood effects. DhakaNest's ranking
reasons additionally require a different evaluation of fidelity and usefulness.
[P18](https://arxiv.org/pdf/1705.07874).

Structured validation research explains why random holdouts and unseen-area or
future-market transfer estimate different tasks. CQR and jackknife+ require
assumptions and additional calibration/resampling procedures. Their guarantees
do not attach automatically to a saved point model, nor do marginal guarantees
ensure every neighborhood is calibrated.
[P27](https://doi.org/10.1111/ecog.02881),
[P29](https://arxiv.org/pdf/1905.03222),
[P30](https://doi.org/10.1214/20-AOS1965).

## Required DhakaNest evidence

- Preserve the untouched official test and record its historical selection role.
- Reuse frozen predictions for residual, rent-band, size-band, and geographic
  analysis; define bands using development evidence.
- Report bias, median/p90 errors, support counts, and fallback routes in addition
  to aggregate MAE/RMSE.
- Audit outliers without deleting inconvenient errors or tuning against test
  outcomes.
- Label bootstrap uncertainty conditional on the fixed model separately from
  training-pipeline variance, following P28.
- Treat model-based rent reasonableness as an uncertain input whose usefulness
  must pass H4C, not as verified market truth or demographic fairness.

These analyses remain future work. No model loading, retraining, prediction
generation, or official-test reselection occurred in Phase 2.
