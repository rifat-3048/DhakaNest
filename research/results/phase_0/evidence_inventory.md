# Phase 0 Evidence Inventory

The machine-readable inventory is `research/datasets/evidence_inventory.json`.

## Verified and reusable

| Evidence | Verified facts | Provenance |
|---|---|---|
| Raw rental data | 28,800 records; SHA-256 `bcd4590a...f0078b` | `ml/data/raw/houserentdhaka.csv`; raw manifest |
| Prepared rental data | 15,248 records after 13,541 exact duplicates and 11 invalid records; SHA-256 `451eecf5...08573` | `ml/data/processed/dhakanest_rent_training_v1.csv`; preparation manifest |
| Frozen splits | Train 10,668; validation 2,289; untouched test 2,291; unseen challenge 1,119; seed 42 | `ml/data/splits/`; preparation manifest and checksums |
| Candidate comparison | Random Forest, CatBoost, XGBoost; XGBoost selected by validation MAE 3,571.57 BDT | Candidate metric files and `winner_selection_manifest.json` |
| Production model | XGBoost bundle 1.0.0, log1p target, 468 estimators, 12,957 production-training rows, zero official-test rows used in retraining | `final_production_manifest.json` and `ml/exports/` |
| Official test | MAE 3,193.69 BDT; RMSE 7,667.50 BDT; R2 0.9001; MAPE 11.88%; one recorded test evaluation | Test manifest, metrics, predictions, comparison report |
| Local research evidence | 53 files: 7 manifests, 26 metric/data outputs, 3 reports, and 17 PNG figures | `ml/evidence/` file and checksum audit |
| Synthetic inventory | Deterministic generator seed 20,261,005; default 2,500 active and 100 lifecycle listings; stored coverage report | `academic_inventory_service.py`; `academic_inventory_coverage.json` |

The raw, processed, split, and official-test counts above are supported by
artifacts and checksums, not only narrative documentation.

## Available but requiring validation

- Recommendation labels are frozen in
  `backend/evaluation/recommendation_ground_truth.json` (SHA-256
  `2589d957...ad9c`): 8 profiles x 12 properties = 96 judgments. Complete
  listing records and route matrices are absent, so the ranking is not an
  offline-frozen benchmark.
- The August 27 result file records Precision@5/10 `0.9500` and NDCG@5/10
  `0.9822`, but predates WSM v3 and v4 and has no run manifest.
- The connected Google Drive folder was accessible for metadata inspection.
  Local names and sizes align with the primary manifests/evidence. Equality of
  every external copy was not checksum-verified.
- Drive contains useful external-only interim cleaning tables, dataset-audit
  tables, location reference/alias files, split summaries, and segment
  evaluations. Import only selected files in a later, declared experiment;
  do not duplicate the full training tree.
- The October 7 paper draft reports NDCG `0.9615` and describes a rent-plus-
  travel affordability phase. No raw ranking output or manifest was found for
  that value.

## Missing for future research

- An immutable recommendation benchmark bundle containing the 12 complete
  listing documents and deterministic route matrices.
- A WSM v4 per-profile ranking output, metric audit, configuration, dependency
  versions, and checksums.
- Independent human annotations and inter-rater agreement evidence.
- Baseline, ablation, significance, robustness, and user-study outputs. These
  belong to later phases and were not created in Phase 0.

## External accessibility status

**Verified:** the specified Drive folder and the paper draft were readable via
the connected Google Drive integration during the audit. **Unresolved:** Drive
ownership/visibility and byte-level identity of external-only assets were not
independently verified. No Drive artifact was modified or downloaded into the
repository.
