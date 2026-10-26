# Benchmark Coverage

Measured from `datasets/benchmark_v1/coverage_report.json`:

| Attribute | Observed |
|---|---:|
| Tenant scenarios | 200 |
| Scenario families | 10, each 20 profiles |
| Development / final | 60 / 140 |
| One / two / three destinations | 61 / 70 / 69 |
| Destination references across requests | 408 |
| Importance values | All integers 1-5 |
| Budget flexibility 0 / 5 / 10 percent | 92 / 36 / 72 profiles |
| Maximum budgets | BDT 12,500-80,000 |
| Bedroom minimums 1 / 2 / 3 | 80 / 60 / 60 profiles |
| Bathroom minimums 1 / 2 / 3 | 100 / 80 / 20 profiles |
| Property inventory | 12 evaluation fixtures |
| Profile-property combinations | 2,400 |

All production property types and furnishing values are represented. Move-in
dates cover November/December 2026 and January 2027, plus omitted dates.
Must-have and nice-to-have amenity groups do not overlap. Floor-size targets,
optional minimum rent/area and maximum area, all five WSM priorities, differing
commute bounds and travel frequencies are represented. Full frequency tables
are frozen in `tenant_profile_coverage.json`.

This is coverage-driven design, not population sampling. Requirements are
logically valid but not all can be satisfied by the sparse fixture inventory.
Priorities are family-dependent and conditions are correlated by construction;
this is not an orthogonal causal experiment. Bedroom/bathroom minima 4-6,
all individual canonical amenities, all geographic regions and verified real
institution destinations are not exhaustively represented. The coverage report
must not be presented as evidence of representativeness of Dhaka renters.

The 12 fixtures are not an adequate replacement for the intended large property
snapshot. Competitive Top-10 evaluation is unavailable: every profile has fewer
than ten hard-filter survivors. Additional independently sourced/de-identified
inventory and route evidence are required before annotation and evaluation.
