# Candidate Feasibility

Production base eligibility and hard filters are reused without changing their
semantics. Per-property singleton diagnostics record the **first sequential
exclusion reason**, not every possible failed condition. Candidate records keep
pre-filter, base-eligible, hard-surviving, routing-accounted, routing-complete,
commute-feasible, missing, unreachable and over-commute groups distinct.
Production `apply_commute_routes` supplies the actual commute constraint check.
KNN and final WSM stages are null/not executed, not empty ranked results.

Measured hard-filter survivor counts:

| Survivors | Profiles |
|---:|---:|
| 0 | 40 |
| 1 | 88 |
| 2 | 44 |
| 3 | 28 |

Minimum=0, median=1, maximum=3. Profiles with >=10 survivors=0; fewer than
10=200. The 40 zero-survivor profiles are known empty before routing. For 160
others commute feasibility is unknown; neither the commute-feasible distribution
nor counts above/below ten are claimed. No profiles are adjusted to force ten
results. The fixed design permits valid sparse cases, but the observed 20%
zero rate is a fixture limitation, not an estimate of market search failure.

## Candidate comparability

End-to-end future methods start from the same frozen inventory and apply their
declared eligibility/routing stages. Area-first is never restricted to the
proposed method's selected KNN set. Controlled ranking comparisons share the
hard-and-commute-feasible pool only when routing is verified. End-to-end and
controlled results must remain separate estimands. Missing routes block a
route-complete comparison rather than silently shrinking the reference universe.

Current inventory competition is inadequate for Top-10 claims. Before Phase 4,
obtain the authorized larger snapshot, genuine assessments and road matrix,
repeat feasibility checks in a new version, and explicitly retain/stratify
legitimate sparse queries under the amendment.
