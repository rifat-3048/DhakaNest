# Commute Candidate Coverage

Status: BLOCKED. Research-only implementation exists, but host virtualization/engine prerequisites prevent genuine local OSRM execution. No route measurements were manufactured.

Hard-filter competition remains verified: all 200 profiles have >=10 candidates,
range 55-1512, median 336.5. Post-routing completeness/commute-feasible minimum,
median, maximum and bins 0/1-4/5-9/>=10 remain UNKNOWN for all 200 profiles.
Profiles with ten commute-feasible homes: UNKNOWN, not zero or 200.
No profile, date, commute threshold, WSM or KNN mathematics was changed.

Existing candidate reports preserve development/held-out, 1/2/3 destinations and
strict/flexible groups. Only genuine acquired routes can populate those commute
counts. After local capture, reuse the existing production filter/commute logic,
retain zero/sparse cases and report exclusions, unresolved pairs and unreachable
routes separately. No final ranking/quality experiment was performed. Source tools: research/routing/osrm_local/. Data: benchmark_v1_3 reference overlay and its immutable benchmark_v1_2/v1_1 parents.
