# Phase 0 Methodology Discrepancies

## WSM budget methodology

### Current production behavior: verified

`backend/app/services/wsm_service.py` declares
`RECOMMENDATION_SCORING_VERSION = "wsm_v4"` and calculates:

```text
budget_score = clamp(1 - advertised_rent / maximum_rent_budget, 0, 1)
```

The caller passes `candidate.asking_rent_bdt`; minimum rent and transportation
cost do not enter the criterion. Monthly travel cost and advertised rent plus
travel are still calculated for display. WSM combines exactly location,
budget, space, amenities, and rent fairness.

Regression coverage in `backend/tests/test_recommendation_part5.py` verifies
bounded/monotonic budget scores, minimum-rent independence, travel-cost display,
travel not changing rent affordability, and the `wsm_v4` version. History tests
verify that snapshots record `wsm_v4`.

Current local documentation in `backend/README.md`, `docs/architecture.md`, and
`docs/report-update-notes.md` agrees with v4. The connected Google Drive paper
draft is stale: it describes budget affordability using rent plus travel and
reports results from before the v4 change.

### Version chronology: verified

| Date | Commit/evidence | Methodology status |
|---|---|---|
| 2026-08-27 | `a4286b3` evaluation documentation | `0.9822` recorded before WSM v3/v4 existed |
| 2026-10-05 | `62eb57c` | WSM v3 introduced travel frequency and used total monthly spend when complete; otherwise legacy rent logic |
| 2026-10-07 | Drive paper draft | Reports `0.9615` and describes rent-plus-travel/legacy affordability |
| 2026-10-11 | `6badfb8` | WSM v4 changed budget to advertised rent versus maximum budget only |

The current evaluator imports the current production pipeline, so an invocation
today would use WSM v4. That does not retroactively make older result files v4.

## NDCG discrepancy

### Shared metric and benchmark facts

- Current ground truth is version `recommendation-evaluation-v1`, with 8
  profiles, 12 identifiers, and 96 complete 0-3 relevance labels.
- `ndcg_at_k` uses `(2^relevance - 1) / log2(rank + 1)` and compares the returned
  ranking with the ideal ordering of all judgments.
- Precision treats relevance 2 or 3 as relevant.
- Git comparison found no content difference in the ground-truth JSON between
  the August evidence commit and current `HEAD`.

### `0.9822`: verified historical artifact, not current-v4 proof

The exact value exists in
`docs/evidence/evaluation/recommendation-evaluation.txt` and
`docs/final-results.md`. Git dates the evidence to August 27, before the WSM v3
and v4 commits. It therefore belongs to the earlier production scoring
implementation. No run manifest records listing snapshots, route responses,
dependencies, or a scoring-version field.

### `0.9615`: verified paper claim, run provenance unresolved

The value exists in the connected Google Drive paper draft dated October 7.
The paper describes the rent-plus-travel methodology associated with the WSM v3
period and notes backward-compatible rent-only behavior in the benchmark.
Chronology makes a v3-era run plausible. However, no repository or Drive raw
evaluation output, per-profile ranking, checksum, or execution manifest was
located. It cannot be conclusively assigned to a particular invocation.

### Resolution

Both numbers are legitimate **historical claims**, but they are not directly
comparable as current WSM v4 evidence. The label file and metric formula appear
stable; candidate listing state, routes, and scoring implementation are not
frozen in either result. The only reproducible portions from current frozen
evidence are ground-truth validation and the pure metric formulas.

**Unresolved:** the current WSM v4 NDCG. Reproduction was intentionally stopped
because the CLI would read MongoDB listing documents and call OSRM. Running it
would violate the requirement to avoid unverified external state and would
still not create a fully reproducible result.

Before publication, freeze complete listing fixtures and route matrices, run
the unchanged v4 pipeline offline, and retain per-profile rankings plus a
manifest. Preserve `0.9822` and `0.9615` with explicit historical labels rather
than overwriting either value.
