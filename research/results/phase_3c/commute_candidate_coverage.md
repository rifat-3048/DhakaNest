# Candidate Coverage

Status: partially complete. Endpoint acquisition is blocked by missing explicit workload permission and verified endpoint-specific matrix limits. No live route request was sent.

Measured hard-filter bins: zero=0, 1-4=0, 5-9=0, >=10=200; minimum=55,
median=336.5, maximum=1512. The exact original 200 requests and 60/140 split
are preserved. No KNN/WSM ranking or held-out quality analysis was run.

Commute-feasible bins, minimum/median/maximum and >=10 count remain UNKNOWN
for all 200 profiles. Missing routes are not commute failures or zero candidates.
candidate_coverage.json reports separate hard/commute stages for development
versus held-out, 1/2/3 destinations and strict/flexible requirements. Strict means
at least one supplied commute cap <=30 minutes; this descriptive label is not
a post-hoc performance pass threshold. K=10 competition is established before
routing only, not after constraints. No difficult profile was removed.

After authorized genuine capture, existing production hard filtering and commute
constraint utilities are reused for all profiles. Inputs: research/datasets/benchmark_v1_1 (checksum-referenced unchanged) and benchmark_v1_2/routing. Code: research/benchmark/phase3c.
