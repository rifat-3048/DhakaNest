# Offline Fixture Verification

Status: partially complete. Endpoint acquisition is blocked by missing explicit workload permission and verified endpoint-specific matrix limits. No live route request was sent.

RoutingFixture loads verified parent data and overlay logical/physical maps.
It exposes the existing frozen RoutingProvider interface, expands verified
physical results to exact logical IDs, checks raw capture provenance and can
prepare production-compatible candidates. Parent references bind properties,
assessments, profiles, split and destinations. WSM v4 and K=10 remain unchanged.

Offline loading works without MongoDB, OSRM, frontend or production credentials.
require_ready() fails on missing evidence; the provider has no live fallback.
New tests check coordinate direction, units, production parser behavior,
30-minute boundary constraints, ordering and known/missing separation. Existing
importance/WSM regressions also pass. Future ready inputs can be prepared, but
no final rankings, NDCG, Precision, Recall, baselines or ablations were run.
Overlay reproduction is byte-identical. Inputs: research/datasets/benchmark_v1_1 (checksum-referenced unchanged) and benchmark_v1_2/routing. Code: research/benchmark/phase3c.
