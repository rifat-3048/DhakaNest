# Phase 3B Implementation Dependency Map

Audited before reconstruction: Phase 3A tool guide, sealed benchmark_v1 and
v2 phase manifest, amendment, reports, tests, Phase 0 code audit/reuse plan,
production academic generator, listing/request schemas, rent assessment and
inference helper/model manifest, routing URL/parser, candidate/accessibility,
KNN and WSM v4 paths. Historical baseline checks actually rerun: 75 research
tests and 96 backend part 1/2/5/7 tests pass; 51 Phase 3A output hashes and
44 Phase 0-2 output hashes match.

| Dependency | Available evidence / action |
|---|---|
| Tenant requests/split | Preserve original 200 requests and 60/140 split bytes |
| Inventory | Existing pure generate_inventory with seed 20261005, 2500 active + 100 lifecycle, generator 1.0.0; reconstruct offline |
| Assessments | Existing frozen XGBoost/preprocessors/helper with manifest checksums; fresh inference now explicitly authorized |
| Coordinates | Retain original 12 anchors and deterministic synthetic jitter; label approximation, no fresh geocoding |
| Hard filtering/commuting | Reuse Phase 3A construct_candidates and production pure eligibility/filter/commute functions |
| Common pooling | Reuse blinding/export/dedup; add quota sampler so random/boundary cases are not crowded out by dense strata |
| Offline loader | Subclass sealed loader; add parent-byte, inference-provenance and route-coordinate checks |
| Route evidence | Genuine OSRM capture requires separate endpoint-specific authorization; prepare full pair manifest and opt-in acquisition wrapper |
| Live database snapshots | Not authorized or needed for deterministic reconstruction; no MongoDB access |
| Exact POIs/real properties | Not independently verified; external geocoding/private records cannot be acquired automatically |

All extensions are new files under research/benchmark/phase3b, with tests and
results inside research/. Existing source is checksum-sealed, so extending it
through a versioned package preserves historical code and avoids manifest churn.
No ranking, labels, baselines or superiority evaluation are part of this phase.
