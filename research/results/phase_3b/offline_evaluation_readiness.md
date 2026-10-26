# Offline Evaluation Readiness

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

BenchmarkFixture extends the sealed Phase 3A loader without edits. It validates
dataset/source hashes, byte-identical parent profiles/splits, actual-model
assessment provenance, synthetic coordinate precision and pair-coordinate
bindings. It loads all 2500 active properties, 200 profiles, 12 destinations,
30,000 route status rows and legitimate stored reconstruction assessments.
prepared_inputs(profile_id) returns deterministic candidate data and versions
(WSM v4, K=10, amended protocol 1.1.0-phase3), without ranked outcomes.

Works without MongoDB, a frontend, deployment, production credentials or live
OSRM. Missing routing causes require_experiment_ready to fail clearly, with no
fallback. The saved model is needed for provenance/replay, not runtime retraining.
The original budget formula clamp(1-rent/max_budget,0,1) is unchanged; travel
spending remains informational. Direct scalar regression tests confirm v4
behavior, not a second implementation or a ranking benchmark.

An opt-in capture wrapper records raw evidence, versions/statuses, logs and
route-pair metadata. attach_capture publishes another new integrated version,
rechecks raw responses and reconstructs candidates/pools. Genuine integration
was not executed because routing acquisition is not authorized. Prepared inputs
are functional; a fully experiment-ready matrix is still unavailable.
