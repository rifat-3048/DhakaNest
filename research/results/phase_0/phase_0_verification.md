# Phase 0 Verification

## Created

- Isolated `research/` workspace documentation and protocol examples.
- Standard-library experiment manifest utility with dataset/output checksums,
  timestamp, Git commit, seed, versions, dependencies, status, and safety data.
- Safe workspace initializer with no application imports.
- Machine-readable evidence inventory.
- Seven automated safety/reproducibility tests.
- Five required Phase 0 reports.

## Safety status

| Check | Status |
|---|---|
| Production backend/frontend files modified | No |
| Existing datasets/evidence/model artifacts modified | No |
| MongoDB read or write performed | No |
| OSRM/network recommendation request performed | No |
| Recommendation/history run generated | No |
| Model training or deployment performed | No |
| Research output overwrite protection | Implemented with exclusive file creation |
| Research path containment | Implemented and tested |
| Database write configuration | Rejected and tested |

## Verification classification

- **Verified:** repository architecture, current WSM v4 implementation and
  tests, local data/model manifests, model metrics, benchmark label dimensions,
  metric formulas, Git chronology, and Drive metadata described in the reports.
- **Unresolved:** the exact raw execution that produced paper NDCG `0.9615` and
  the present WSM v4 NDCG.
- **Requires external evidence:** a frozen copy of complete benchmark listing
  documents and deterministic route matrices, plus raw run metadata for the
  paper result if it exists.

## Intentional non-execution

`backend/scripts/evaluate_recommendations.py` was not run. Although its
evaluation adapter is read-only, the CLI reads mutable local MongoDB seed
documents and defaults to an external OSRM provider. Its output would not meet
the requested frozen-evidence standard.

## Test results

Executed with the backend virtual environment on 2026-10-25:

```text
backend\.venv\Scripts\python.exe -m unittest discover -s research\tests -v
Ran 7 tests in 0.114s - OK

backend\.venv\Scripts\python.exe -m unittest \
  tests.test_recommendation_part5 tests.test_recommendation_part7 -v
Ran 50 tests in 0.170s - OK
```

The first suite verifies configuration validation, checksum stability, manifest
metadata, JSON serialization, workspace path containment, exclusive writes,
database-write rejection, and initialization without live database modules.
The backend suites verify WSM v4, travel-cost separation, the five-factor sum,
ranking, evaluator read-only behavior, ground-truth validation, and metric
formulas. JSON syntax validation also passed for both protocols and the evidence
inventory.

The full application test suite was not required or run. No test required a
live database or external route provider.
