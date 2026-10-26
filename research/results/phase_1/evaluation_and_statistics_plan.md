# Evaluation and Statistical Analysis Plan

## Relevance and ranking metrics

Independent annotators use ordinal labels: 0 not suitable, 1 marginal, 2
suitable, and 3 highly suitable. Binary metrics treat labels 2 and 3 as
relevant.

NDCG uses gain `2^relevance - 1` and discount `log2(rank + 1)`. NDCG@5 and
NDCG@10 are primary benchmark metrics. The ideal list is drawn from all judged
properties in the common profile universe. Unreturned ranks receive zero gain.

Precision@K divides relevant results by fixed K, even when fewer than K are
returned. Recall@10 uses all relevant judged properties as its denominator.
MAP@10 divides accumulated precision at relevant ranks by `min(R, 10)`. MRR is
zero when no relevant item is returned; Hit Rate@10 is binary per profile.
Coverage, empty-result rate, commute satisfaction, and attrition are always
reported. Diversity is exploratory and requires frozen feature definitions.

Profiles with no relevant judged property are excluded from NDCG, Recall, MAP,
and MRR aggregates but counted and reported; they remain in coverage results.
Primary aggregation is macro averaging so every tenant profile receives equal
weight. Micro results may appear only as labeled sensitivity analyses.

This protocol intentionally differs from the historical evaluator, whose
short-list Precision denominator is the number returned. Future results need a
new metric/protocol version and must not overwrite historical files.

## Prespecified inference

The paired unit for recommendation comparisons is the tenant profile. The
primary estimand is mean paired NDCG@10 difference.

- Compute two-sided 95% profile-level bootstrap confidence intervals with
  10,000 paired resamples, seed 42; use BCa intervals when stable and percentile
  intervals otherwise.
- Use a paired randomization/permutation test, exact when feasible or 10,000
  recorded sign permutations.
- Use Wilcoxon signed-rank as a sensitivity analysis when nonzero-pair and tie
  conditions permit.
- Report mean and median paired differences plus paired rank-biserial effect
  size. Do not report p-values without effects and intervals.
- Apply Holm family-wise adjustment within each research-question comparison
  family. Report raw and adjusted values.
- Treat two-sided alpha 0.05 as a prespecified conventional decision rule, not
  evidence or an expected result.

Random-baseline trials are averaged per profile before comparisons. Missing
ranks are not imputed. Unjudged properties are not assigned relevance zero.

## Sensitivity and robustness

Prespecified analyses include candidate-pool resampling, small budget changes,
bounded route/coordinate perturbations, seeds, duplicate-cluster removal, and
real-only versus synthetic-only subsets. Subgroups cover destination count,
budget, Dhaka region, property type, commute strictness, and source type.
Sparse groups receive estimates and uncertainty with an explicit limitation,
not post hoc significance claims.

For connection to older work, returned-count Precision may be shown only as a
labeled sensitivity result. It cannot replace fixed-K primary evaluation.

## User study and XGBoost

User study outcomes account for repeated participants and tasks. The primary
ordinal selected-property relevance model includes workflow and period effects,
with participant/task random effects when estimable. Continuous and binary
outcomes use suitable mixed models or prespecified paired robust alternatives.

XGBoost aggregate and subgroup errors receive bootstrap intervals. Test data
remain confirmatory and cannot drive new model selection. Segment contrasts are
adjusted within rent, size, and geography families.

Inconclusive findings are reported with estimates, intervals, adjusted p-values,
coverage, and power limitations. Failure to reject is not equivalence. Null,
negative, and adverse prespecified outcomes remain in the final report.
