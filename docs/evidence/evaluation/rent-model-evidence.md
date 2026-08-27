# Rent Model Evidence

Source: checked-in ML manifests and exported bundle metadata.

| Model | Validation MAE (BDT) |
| --- | ---: |
| Random Forest | 3,721.74099 |
| XGBoost | 3,571.57303 |
| CatBoost | 3,635.50254 |

Final XGBoost official test: MAE 3,193.69256 BDT; RMSE 7,667.50210 BDT;
R2 0.900087; MAPE 11.883525%. Bundle version is `1.0.0`, target strategy is
`log1p`, and the primary production-model SHA-256 is
`e63b4c21791a285dba4a3902799358964f3559c4fc73b8eb04479fdcaf9ebbc9`.

The predictor loaded successfully during Part 12. Recommendation code reads
the stored assessment and does not rerun XGBoost.
