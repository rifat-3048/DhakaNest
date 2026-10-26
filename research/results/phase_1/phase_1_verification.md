# Phase 1 Verification

## Scope completed

- Defined the destination-first research contribution without claiming novelty
  from algorithm combination alone.
- Specified six research questions and eight null/alternative hypotheses.
- Operationalized eight comparison methods and nine ablations.
- Fixed future metric, benchmark, annotation, statistics, XGBoost, and user-study
  protocols in machine-readable JSON and human-readable plans.
- Added cross-file validation for identifiers, references, metric conventions,
  required primary hypotheses, and safe output paths.

## Integrity decisions

- WSM v4 is the production reference. Travel frequency remains informational.
- Historical NDCG `0.9822` and `0.9615` are not presented as WSM v4 evidence.
- Synthetic and real observations remain separately identified.
- Relevance labels must come from blinded independent humans, never DhakaNest
  scores or explanations.
- Rent Fairness means stored XGBoost rent reasonableness, not demographic
  fairness.
- Official test data cannot be reused for model selection.
- Future Precision@K uses fixed K; historical returned-count results remain
  separately versioned.

## Non-regression

No production backend/frontend file, database record, model artifact, dataset,
Phase 0 report, or historical output was changed. No recommendation, baseline,
ablation, training, routing, annotation, user study, or deployment was run.

## Test results

Executed with the backend Python 3.12 virtual environment on 2026-10-25:

```text
python -m research.protocols.validate_protocols
Status: OK (8 files, 6 questions, 8 hypotheses, 8 baselines,
9 ablations, 12 metrics)

python -m unittest discover -s research/tests -v
Ran 14 tests in 0.129s - OK

python -m unittest tests.test_recommendation_part5 \
  tests.test_recommendation_part7 -v
Ran 50 tests in 0.107s - OK
```

All eight protocol files also passed `json.tool` syntax checks. The new Python
utility and test pass bytecode compilation. Every Phase 0 output checksum still
matches its immutable Phase 0 manifest.

The existing backend tests intentionally confirm that the historical evaluator
uses returned-count Precision for short lists. The Phase 1 journal protocol
prespecifies fixed-K Precision under a new evaluation version; production code
was not changed.

## Unresolved decisions

- Final profile count within the 100-300 target requires annotation-pilot and
  resource evidence.
- Annotation pool size requires a workload and coverage pilot.
- User-study sample size requires a priori power analysis and ethics review.
- SHAP feasibility depends on saved-bundle compatibility and a pinned dependency.
- Current WSM v4 benchmark performance remains unknown until complete listing
  fixtures and route matrices are frozen.

Phase 1 produces designs only. It does not authorize Phase 2 literature work or
later experiments.
