# Local Routing Acquisition

Status: BLOCKED. Research-only implementation exists, but host virtualization/engine prerequisites prevent genuine local OSRM execution. No route measurements were manufactured.

Logical and physical workload remains 30,000 pairs, no exact duplicates.
Proposed local server table-size 100 permits the planned 52-coordinate batches
by configuration, pending actual startup and smoke. Existing 40x12 cells gives
63 full requests, 189 with retries, plus one separate 2x2 smoke request.
Actual HTTP requests to local/public route endpoints=0, genuine successes=0,
verified unreachable=0, failed requests=0; missing pairs=30,000.

The local operator restricts capture to http://127.0.0.1:5001 and reuses Phase
3C acquisition/checkpoint/retry/raw-validation logic. Approval is scoped only
after a verified graph and successful smoke on the same isolated container.
Data hash, binary/image identity and graph hash accompany the scoped config.
Missing/failed/unreachable remain distinct. No public demo fallback exists.
The user authorized local capture, but absent host prerequisites prevent it.
Source tools: research/routing/osrm_local/. Data: benchmark_v1_3 reference overlay and its immutable benchmark_v1_2/v1_1 parents.
