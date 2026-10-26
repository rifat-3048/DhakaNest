# Experimental Design

## Frozen inputs and comparison modes

Every recommendation method receives the same versioned tenant profiles and
starting property snapshot. Route-aware methods consume one frozen OSRM matrix.
Labels are produced independently before evaluators expose method identities or
scores. All methods return at most 10 items and use stable identifier tie breaks.

Two questions must not be mixed:

- **End-to-end comparison:** each method may select a different set from the
  common universe. Report every attrition stage, coverage, and empty results.
- **Controlled reranking:** methods receive exactly the same candidate set so
  only ordering changes.

Common safety and mandatory eligibility remain enabled unless the named
intervention explicitly targets a rule. A KNN-free method receives all eligible
commute-valid candidates; it is not forced through the production shortlist.

## Operational baselines

| ID | Operation |
|---|---|
| B_RANDOM | Uniform permutation of eligible candidates over 1,000 trials, seed `42 + trial_index`; summarize trials before profile aggregation |
| B_FILTER | Mandatory filters only; newest timestamp first, missing timestamps last, identifier tie break |
| B_AREA_FIRST | Declared neighborhood tier, then broad area, then outside area; within tier rank by distance from maximum budget, recency, identifier |
| B_KNN_ONLY | Production feature construction and K=10 cosine shortlist; rank by similarity only |
| B_WSM_ONLY | Route/commute survivors ranked by WSM v4 without a KNN shortlist |
| B_NO_DESTINATION | Non-route eligibility, KNN, then four-factor WSM with location removed and remaining priorities renormalized |
| B_NO_RENT_FAIRNESS | Full shortlist, four-factor WSM with Rent Fairness removed and remaining priorities renormalized |
| B_FULL | Unchanged production hard filters, frozen routes, destination score, KNN K=10, and five-factor WSM v4 |

The area-first neighborhood is declared with the profile before rankings and
annotation. It is never inferred from DhakaNest output. Route-aware methods use
identical route assumptions. Random results are repeated rather than reported
from a favorable single seed.

## Ablation matrix

| ID | Intervention | Controlled interpretation |
|---|---|---|
| A_FULL | None | Production anchor |
| A_NO_KNN | Send all eligible commute-valid candidates to WSM | KNN shortlist quality and efficiency |
| A_EQUAL_DESTINATION_IMPORTANCE | Replace priorities with equal destination weights | Destination importance only |
| A_NO_COMMUTE_CONSTRAINTS | Retain route scores but stop commute-limit rejection | Constraint relevance/coverage tradeoff |
| A_NO_DESTINATION_LOCATION | Remove routing/location and renormalize four WSM criteria | Combined destination-location effect |
| A_NO_RENT_FAIRNESS | Remove criterion, renormalize remaining priorities | Stored rent-reasonableness contribution |
| A_NO_AMENITIES | Remove nice-to-have criterion, retain must-have filter, renormalize | Soft amenity contribution |
| A_NO_PREFERRED_FLOOR_SIZE | Average bedroom/bathroom space components only; retain hard size limits | Soft size matching contribution |
| A_NO_TRAVEL_FREQUENCY | Suppress informational monthly travel/total spend only | Exact ranking-invariance and user-information check |

Travel frequency is not a WSM v4 ranking factor. Its removal cannot be
presented as a ranking ablation unless a separately labeled experimental method
explicitly changes production methodology.

## Fairness and leakage controls

- Preserve a common universe while allowing each intended algorithm to select
  its own candidate set.
- Freeze profiles, listings, routes, random seeds, configuration, and labels.
- Keep final-evaluation profiles sealed while developing implementations on the
  development partition.
- Blind annotators to method, rank, similarity, criterion values, and final
  suitability.
- Use fixed-K precision and zero gain for absent ranks; report coverage and
  empty-result rates.
- Retain real and deterministic synthetic source labels and report them
  separately before any combined estimate.

Phase 1 defines these methods only. It does not implement or execute them.
