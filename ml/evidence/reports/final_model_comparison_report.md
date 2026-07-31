# DhakaNest Final Model Comparison

## Candidate Validation Results

| model         |   validation_mae_bdt |   validation_rmse_bdt |   validation_r2 |   validation_mape_percent |   validation_median_ae_bdt |   validation_p90_ae_bdt |
|:--------------|---------------------:|----------------------:|----------------:|--------------------------:|---------------------------:|------------------------:|
| XGBoost       |              3571.57 |               8842.54 |            0.84 |                     12.68 |                    1689.22 |                 6454.96 |
| CatBoost      |              3635.5  |               9238.22 |            0.83 |                     12.73 |                    1621.41 |                 6519.85 |
| Random Forest |              3721.74 |               9009.87 |            0.84 |                     13.6  |                    1792.66 |                 6854.29 |

## Selection Decision

XGBoost was selected because it achieved the lowest validation MAE, which was
the primary model-selection metric. It also achieved the strongest validation
RMSE, R², MAPE, and P90 absolute error among the three candidates.

CatBoost achieved the lowest median absolute error but did not outperform
XGBoost on the primary validation metric.

## Official Test Result

- Model: XGBoost
- Rows: 2,291
- MAE: BDT 3,193.69
- RMSE: BDT 7,667.50
- R²: 0.9001
- MAPE: 11.88%
- Median AE:
  BDT 1,594.67
- P90 AE:
  BDT 6,070.58

## Final Production Export

The production XGBoost model was retrained using 12,957 training and validation
records. The official test records were not included.

The final export contains:

- Primary XGBoost model
- Broad-area fallback model
- Dhaka-wide fallback model
- Three matching preprocessors
- Routing metadata
- Feature schema
- Inference helper
- Exact software requirements
- Model card
- Checksums and production manifest
