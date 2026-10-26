# Routing Completion and Authorization Request

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

Required unique full-grid route pairs: 30000.
Genuine valid=0, supported unreachable=0, failed attempted=0, missing=
30000. No OSRM or geocoding endpoint was contacted. Missing
values remain null/status missing, not zero, unreachable, or straight-line routes.
Full-grid freezing supports future alternative candidate universes beyond KNN.

The route manifest binds stable pair IDs, listing/destination IDs, exact frozen
origin/target coordinates and driving profile. Route rows preserve source,
status, duration/distance, acquisition timestamp, engine/map version (unknown
until acquired), and explicit failure reason. Pair IDs eliminate duplicate pairs.

Production URL/parser and sealed capture machinery are reused: bounded serial
concurrency 1, 40 origins/20 destinations per request, one-second minimum pacing,
30-second timeout, two retries and immutable checkpoint/resume. Mocked tests
verify successes, failures, unreachable nulls, interrupted resume and raw-evidence
integrity; those artificial test values are never benchmark evidence.

Separate authorization needed: approve an OSRM endpoint for this research
capture, driving profile and 30,000 frozen pairs. Planned requests=
63, maximum with two retries=
189. Minimum pacing about one minute
plus service time; an all-timeout/retry path can approach 102 minutes. Approve
appropriate provider capacity and record engine/map versions where available.
The example http://127.0.0.1:5000 is not known to be running. Local operation
without Docker is supported; no server/deployment/package installation was run.

Use the opt-in command documented in benchmark/phase3b/README.md only after
explicit endpoint permission. Integrate genuine capture through attach_capture
into another new dataset version. Current benchmark must remain marked partial.

Evidence: routes.jsonl, route_pair_manifest.jsonl, routing_acquisition_plan.json,
routing_matrix_metadata.json, routing_matrix_validation.json, failure/log files.
