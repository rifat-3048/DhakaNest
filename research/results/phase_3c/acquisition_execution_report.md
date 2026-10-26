# Acquisition Execution

Status: partially complete. Endpoint acquisition is blocked by missing explicit workload permission and verified endpoint-specific matrix limits. No live route request was sent.

Planned requests=63; actual routing requests=0;
request failures=0; genuine successes=0; supported unreachable=0. Documentation
lookups were performed separately and are not routing acquisition. No claim of
a failed route/endpoint is made from an unattempted request.

New transport controls add scope-bound operator/user approval, cell/coordinate
caps, exact physical dedup, persistent request reservations, bounded retries,
timeout, pacing, redirect refusal and immutable raw checkpoints. URL generation
and response parsing reuse production functions. HTTP 200 does not bypass
matrix/schema/finite-value checks; fallback-speed estimates are rejected.
Temporary provider failures, invalid requests, missing and unverified responses
remain distinct. Interrupted reservations count against the total ceiling.
Resumes verify checkpoints and perform no repeat request for a saved success.
Mocked responses are temporary unit fixtures, never genuine route evidence.

Exact next authorization: endpoint/operator workload consent, verified coordinate
and cell limits, rate and billing constraints, supplied as reviewed evidence
with hashes and approval bound to scope a1a86259264864673f4731d63a8d813787aa466d59e97e74754b764574737371 or a revised
plan hash after updating limits. No server installation or paid commitment is
authorized automatically. See README for the opt-in workflow.
Inputs: research/datasets/benchmark_v1_1 (checksum-referenced unchanged) and benchmark_v1_2/routing. Code: research/benchmark/phase3c.
