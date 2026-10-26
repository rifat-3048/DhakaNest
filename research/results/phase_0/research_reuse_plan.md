# Phase 0 Research Reuse Plan

## Safe reuse boundary

Future experiments should call deterministic service functions beneath the API
layer and supply explicit, checksummed fixtures. They must not import route
handlers, database dependencies, seed/apply scripts, or history persistence.

1. Freeze complete candidate listing documents as a versioned research input.
2. Freeze OSRM table responses or normalized route matrices for every benchmark
   profile and candidate coordinate set.
3. Validate both fixtures and the existing relevance labels before evaluation.
4. Build schema objects through a small research adapter; inject a deterministic
   `RoutingProvider` into the existing evaluator.
5. Run existing hard filtering, location scoring, KNN, WSM, and explanation
   code unchanged. Record the production scoring constant in every manifest.
6. Compute metrics through `recommendation_metrics.py`, save per-profile ranked
   audits, then create an immutable experiment manifest.

## Component decisions

| Component | Plan |
|---|---|
| Hard filters | Reuse pure `filter_recommendation_candidates`; compare outputs against explicit fixtures. |
| OSRM | Do not call live OSRM in publication experiments. Capture routes once under a declared protocol, then inject a deterministic read-only provider. |
| Location score | Reuse current scoring with frozen route measurements. |
| KNN | Reuse production feature builder and neighbor selection; record K, library versions, and tie ordering. |
| WSM | Reuse v4 criterion/ranking functions; adapter must provide controlled settings without editing production code. |
| Rent prediction/fairness | Reuse the checksummed XGBoost bundle only for a separately declared analysis; recommendation experiments should consume frozen approval assessments exactly as production does. |
| Explanations | Reuse deterministic reason builder after ranking when explanation evaluation is in scope. |
| History/contact lookup | Exclude; neither affects ranking, and both introduce live MongoDB access. |
| Synthetic inventory | Reuse deterministic generation and coverage functions offline. Never invoke apply/cleanup functions from research. |

## Evidence handling

- Reference large datasets and model binaries by path/checksum instead of
  copying them into `research/`.
- Treat `ml/data/splits/test.csv`, official predictions, and production model
  artifacts as immutable.
- Selectively import external-only Drive tables only when a later protocol
  names their purpose, source, checksum, and destination.
- Write each result to a new path. The manifest helper uses exclusive creation
  and rejects paths outside `research/`.

## Phase boundary

Phase 0 establishes infrastructure and facts only. Phase 1 should define the
research contribution, hypotheses, independent/dependent variables, and a
preregistered mapping from each hypothesis to future evidence. It should not
run a larger benchmark until the offline v4 fixture package is designed and
frozen.
