# XGBoost Analysis Plan

## Frozen starting evidence

Verified Phase 0 evidence contains 28,800 raw records, 15,248 cleaned records,
10,668 training records, 2,289 validation records, and 2,291 untouched official
test records. XGBoost was selected over Random Forest and CatBoost by validation
MAE. Recorded official-test results are MAE 3,193.69 BDT, RMSE 7,667.50 BDT,
R2 0.9001, and MAPE 11.88%.

These are historical predictive results, not proof of current market accuracy,
causal validity, recommendation quality, or demographic fairness.

## Existing reusable evidence

| Analysis | Existing evidence |
|---|---|
| Data cleaning and split provenance | Preparation/raw manifests, data-cleaning and location reports, checksummed train/validation/test files |
| Model selection | RF, CatBoost, and XGBoost CV/validation metrics, predictions, errors, feature importance, learning curves, winner manifest |
| Final model | Bundle 1.0.0 manifest, fixed 468 estimators, preprocessors, fallback models, feature/routing metadata |
| Official test | One-evaluation manifest, predictions, aggregate metrics, largest errors, actual-versus-predicted and residual plots |
| Segment evidence | External Drive contains segment tables, but local equality/content must be validated before reuse |

The official test set remains immutable and cannot select features,
hyperparameters, bands, plots, or another model. Any newly selected analysis
choice must use training/development evidence or be explicitly exploratory.

## Required later analyses

1. Reconstruct dataset distributions, duplicate removal, quarantines, location
   normalization, missingness, rent/size ranges, and split comparability from
   checksummed evidence.
2. Report the exact XGBoost objective, preprocessing, log1p target, categorical
   handling, hyperparameter search space, cross-validation design, fixed 468
   estimators, software versions, and random seeds.
3. Reproduce candidate validation comparisons without opening the official test
   for selection decisions.
4. Verify existing official-test predictions against artifact checksums; compute
   confidence intervals without changing the model.
5. Produce actual-versus-predicted, residual distribution, residual-versus-
   predicted, and calibration-style binned plots from frozen predictions.
6. Define rent and floor-size bands from training/development data before test
   subgroup evaluation. Use canonical geographic segments with sample counts.
7. Report MAE, RMSE, signed bias, median and p90 absolute error, and MAPE with a
   low-rent warning for every sufficiently supported segment.
8. Audit highest-error records, data quality, out-of-support locations, and
   fallback route (micro-area, broad-area, Dhaka-wide) without deleting errors.
9. Present native feature importance with its limitations. Attempt SHAP only if
   the saved model/preprocessor and a pinned compatible dependency reproduce
   predictions; otherwise record the blocker rather than retrain.
10. Describe uncertainty honestly: the point model has no calibrated prediction
    interval, market drift is untested, and residual spread is not an individual
    guarantee.

## Planned inference and integrity

Use record-level bootstrap intervals for aggregate and subgroup errors. Compare
prespecified rent, size, and geographic groups with adjusted contrasts and
sample counts. Treat small groups as descriptive. Analyze real support and
fallback behavior separately.

Feature importance and SHAP explain model behavior, not causal rent effects.
Rent Fairness in recommendations must continue to use frozen stored assessments
for the benchmark; rerunning current predictions would change the research
question and historical listing state.

## Evidence still needed

- Local validation and checksums for external segment/audit tables.
- Prespecified subgroup boundaries derived without official-test optimization.
- Prediction-route metadata joined to each test record, if recoverable.
- A compatible SHAP environment and reproducibility check, if SHAP is pursued.
- New temporally separated market data for any claim about present-day or
  temporal generalization.

No model was loaded, retrained, tuned, or modified in Phase 1.
