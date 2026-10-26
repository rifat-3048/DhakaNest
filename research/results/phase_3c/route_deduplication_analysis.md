# Exact Route Deduplication

Status: partially complete. Endpoint acquisition is blocked by missing explicit workload permission and verified endpoint-specific matrix limits. No live route request was sent.

Measured logical listing/destination pairs: 30000.
Unique directed physical coordinate/profile keys: 30000.
Reusable duplicate pairs: 0. All 2500 generated
origins are distinct for this input; sharing twelve source-area anchors does
not make jittered property coordinates identical. Required physical calculations
remain 30,000. No nearby coordinates were merged or rounded for optimization.
Logical keys contain IDs; physical keys contain exact numeric coordinates,
direction and profile. Maps are validated against the source domain.

Conditional plan: 63 requests, up to
126 retry requests and 189
total. This reproduces the prior 63-request estimate; it is not provider approval.
Planning caps: 40 origins plus 12 destinations, 52 coordinates, 480 cells;
concurrency 1, one-second pacing, 30-second timeout, two retries. Smaller
operator-approved bounds may increase the plan and require a new scope approval.

Evidence: routing/logical_route_pairs.jsonl, unique_physical_routes.jsonl,
request_plan.json. Mock tests also verify true duplicated-coordinate reuse,
nonmerged near-neighbors and distinct reverse/profile keys. Inputs: research/datasets/benchmark_v1_1 (checksum-referenced unchanged) and benchmark_v1_2/routing. Code: research/benchmark/phase3c.
