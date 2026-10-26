# Candidate Coverage

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

Original 200 profiles and 60-development/140-held-out partitions are preserved
byte-for-byte. No preferences were relaxed or optimized for desired outcomes.
All 2500 approved/available active properties enter base eligibility. Existing
production hard filters/commute checks are reused without KNN or WSM execution.

Hard-filter bins: {'five_to_nine': 0, 'one_to_four': 0, 'ten_or_more': 200, 'zero': 0}.
Minimum/median/maximum survivors: 55 /
336.5 / 1512.
Profiles with at least ten HARD survivors: 200.
First sequential exclusion totals: {'after_area': 4980, 'after_bathrooms': 5700, 'after_bedrooms': 59656, 'after_budget': 109348, 'after_furnishing': 89536, 'after_must_have_amenities': 47240, 'after_property_type': 95876}.
These reasons do not count every simultaneous incompatibility. Exact sparse
profile IDs, families and all production stage counts are recorded in
candidate_coverage.json; no sparse queries are silently removed.

Commute bins remain None; profiles with ten
commute-feasible candidates remain unknown, not equal to the hard-filter count.
Unknown-commute profiles: 200. Route-verified
profiles: 0 (empty-hard-set cases require
no route calls). Candidate count before KNN cannot be finalized until routing.
No arbitrary substantial-subset acceptance threshold was invented after seeing
these counts; supervisor benchmark-design review remains necessary.

Evidence: candidate_universes.json, candidate_coverage.json, properties.json,
unchanged tenant_profiles.json/profile_splits.json. End-to-end methods start
from inventory; controlled pools are never the proposed KNN-selected subset.
