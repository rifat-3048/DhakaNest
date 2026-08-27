# Final Results

These model values come from the checked-in ML manifests. Recommendation and
test values are synchronized from the final Part 12 verification run.

## Rent-Model Validation Comparison

| Model | Validation MAE (BDT) |
| --- | ---: |
| Random Forest | 3,721.74 |
| XGBoost | 3,571.57 |
| CatBoost | 3,635.50 |

## Final XGBoost Official Test

| Metric | Value |
| --- | ---: |
| MAE | 3,193.69 BDT |
| RMSE | 7,667.50 BDT |
| R2 | 0.9001 |
| MAPE | 11.88% |

Bundle version is `1.0.0`; the production primary-model SHA-256 recorded in the
manifest is `e63b4c21791a285dba4a3902799358964f3559c4fc73b8eb04479fdcaf9ebbc9`.

## Recommendation Evaluation

| Metric | Macro average |
| --- | ---: |
| Precision@5 | 0.9500 |
| Precision@10 | 0.9500 |
| NDCG@5 | 0.9822 |
| NDCG@10 | 0.9822 |

The benchmark has 8 profiles, 12 seeded listings per profile, and 96 judgments.
Precision uses relevance >=2 and divides by `min(K, returned count)`, so P@5 and
P@10 can match for short result lists. These are recommendation relevance and
ordering metrics, not accuracy, probability, or confidence.

## Automated Tests

| Layer | Tests passed |
| --- | ---: |
| Backend | 243 |
| Frontend | 76 |

## Dataset Splits

| Dataset | Rows |
| --- | ---: |
| Raw | 28,800 |
| Clean processed | 15,248 |
| Train | 10,668 |
| Validation | 2,289 |
| Test | 2,291 |
