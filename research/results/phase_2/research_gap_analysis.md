# Research Gap Analysis

The gap is bounded to the verified literature and the DhakaNest formulation. It
is not an assertion that every prior system lacks a feature.

| Proposed gap or claim | Supporting evidence | What DhakaNest must show |
|---|---|---|
| Explicit destination tradeoffs deserve evaluation in Dhaka rental choice | P04 and P31 already formulate journey-sensitive housing; P10 models a different geographic signal | H2 against strong journey-aware and single-destination controls, with commute satisfaction and coverage |
| Combining content retrieval with personalized utility may help explicit-needs cold starts | P01/P03 already use staged property recommenders; P13 reviews established hybrids | H1/H4A/H4B on independent labels; quality and candidate-loss effects separately |
| Stored predicted-rent reasonableness might add decision value | P20 predicts/explains Dhaka rent; P18 attributes predictions; P27/P29/P30 expose reliability assumptions | H4C and H6, including subgroup errors, anchoring sensitivity, and prediction uncertainty |
| Ranking metrics alone do not establish better decisions | P05/P26 measure tasks and experience; P23 finds baseline sensitivity | H3 with matched information, counterbalanced tasks, and objective selected-property relevance |
| Reproducibility and candidate-pool definition remain essential | P24/P25 analyze sampling effects; P28 analyzes benchmark variance | Frozen listing/routes/configuration; profile-level uncertainty; declared pooled estimand |

## Defensible contribution statement

DhakaNest implements a Dhaka rental decision framework that combines explicit
housing eligibility, one to three weighted destinations, road-network commute
constraints, content KNN selection, five-criterion WSM v4 ranking, stored
XGBoost rent assessments, and criterion-based reasons. The research contribution
will depend on demonstrating the value and limits of this formulation against
appropriate alternatives using independent relevance and user-decision evidence.

## Claims the evidence does not support

- First destination-first or multi-destination housing system: contradicted by
  direct precedents P04/P31 and older location interactions P05.
- First hybrid property recommender: contradicted by P01/P03 and P02/P13.
- First explainable Dhaka rent model: contradicted by P20.
- XGBoost is universally best: P16/P17/P19 support conditional comparison.
- Rent reasonableness is demographic fairness: different constructs.
- A high historical NDCG demonstrates v4 quality: Phase 0 found missing frozen
  v4 evidence; no new evaluation was run in Phase 2.

## Hypothesis-to-literature interpretation

The machine-readable `hypothesis_evidence_map.csv` links all eight actual
hypotheses. H1 uses P01/P03/P23/P25 for credible controls and ranking evidence.
H2 uses P04/P10/P31 for location semantics. H3 uses P05/P26 and the explanation
contrast in P06. H4A/H4B use staged and hybrid precedents P03/P13. H4C uses
model/decision separation rather than published proof of a benefit. H5 uses
P24/P25/P27/P28 for sampling and robustness. H6 uses P14-P20/P27/P29/P30 for
prediction, interpretation, and uncertainty.

These sources justify experiments that could challenge the hypotheses as well
as support them. None supplies a pre-existing DhakaNest effect size. Their
URLs, source sections, and access qualifications remain in the registry.
